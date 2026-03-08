import asyncio
import os
import queue
import threading
from dataclasses import dataclass

import pyttsx3
import requests
import speech_recognition as sr
from dotenv import load_dotenv
from twitchio.ext import commands


load_dotenv()


@dataclass
class Settings:
    twitch_token: str
    twitch_client_id: str
    twitch_nick: str
    twitch_channel: str
    ollama_model: str = "llama3.2:3b"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_timeout_seconds: int = 120
    chat_response_cooldown_seconds: int = 20
    bot_prefix: str = "!"

    @staticmethod
    def from_env() -> "Settings":
        required = {
            "TWITCH_TOKEN": os.getenv("TWITCH_TOKEN"),
            "TWITCH_CLIENT_ID": os.getenv("TWITCH_CLIENT_ID"),
            "TWITCH_NICK": os.getenv("TWITCH_NICK"),
            "TWITCH_CHANNEL": os.getenv("TWITCH_CHANNEL"),
        }
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

        timeout_raw = os.getenv("OLLAMA_TIMEOUT_SECONDS", "120")
        cooldown_raw = os.getenv("CHAT_RESPONSE_COOLDOWN_SECONDS", "20")

        try:
            timeout_seconds = max(15, int(timeout_raw))
        except ValueError:
            timeout_seconds = 120

        try:
            cooldown_seconds = max(0, int(cooldown_raw))
        except ValueError:
            cooldown_seconds = 20

        return Settings(
            twitch_token=required["TWITCH_TOKEN"],
            twitch_client_id=required["TWITCH_CLIENT_ID"],
            twitch_nick=required["TWITCH_NICK"],
            twitch_channel=required["TWITCH_CHANNEL"],
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            ollama_timeout_seconds=timeout_seconds,
            chat_response_cooldown_seconds=cooldown_seconds,
            bot_prefix=os.getenv("BOT_PREFIX", "!"),
        )


class VoiceListener(threading.Thread):
    """Background microphone listener that pushes transcribed text into a queue."""

    def __init__(self, out_queue: queue.Queue[str]) -> None:
        super().__init__(daemon=True)
        self.out_queue = out_queue
        self.recognizer = sr.Recognizer()
        self._stop = threading.Event()

    def run(self) -> None:
        mic = sr.Microphone()
        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)

        while not self._stop.is_set():
            try:
                with mic as source:
                    audio = self.recognizer.listen(source, timeout=2, phrase_time_limit=8)
                text = self.recognizer.recognize_google(audio)
                if text.strip():
                    self.out_queue.put(text.strip())
            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                continue
            except Exception as exc:  # noqa: BLE001
                self.out_queue.put(f"[voice error] {exc}")

    def stop(self) -> None:
        self._stop.set()


class Speaker(threading.Thread):
    """Single-threaded TTS worker to avoid pyttsx3 run loop conflicts."""

    def __init__(self) -> None:
        super().__init__(daemon=True)
        self.queue: queue.Queue[str] = queue.Queue()
        self._stop = threading.Event()
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 195)
        self.engine.setProperty("volume", 1.0)
        self._set_cuter_voice()

    def _set_cuter_voice(self) -> None:
        voices = self.engine.getProperty("voices")
        preferred_keywords = ("zira", "female", "susan", "hazel", "aria")

        for voice in voices:
            descriptor = f"{voice.name} {voice.id}".lower()
            if any(keyword in descriptor for keyword in preferred_keywords):
                self.engine.setProperty("voice", voice.id)
                break

    def run(self) -> None:
        while not self._stop.is_set():
            text = self.queue.get()
            if text == "__STOP__":
                break
            self.engine.say(text)
            self.engine.runAndWait()

    def speak(self, text: str) -> None:
        self.queue.put(text)

    def stop(self) -> None:
        self._stop.set()
        self.queue.put("__STOP__")


class CatVoiceBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        super().__init__(
            token=settings.twitch_token,
            client_id=settings.twitch_client_id,
            nick=settings.twitch_nick,
            prefix=settings.bot_prefix,
            initial_channels=[settings.twitch_channel],
        )
        self.settings = settings
        self.voice_queue: queue.Queue[str] = queue.Queue()
        self.chat_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
        self.voice_listener = VoiceListener(self.voice_queue)
        self.speaker = Speaker()

    async def event_ready(self) -> None:
        print(f"Logged in as: {self.nick}")
        print(f"Listening in: #{self.settings.twitch_channel}")
        print(f"Chat response cooldown: {self.settings.chat_response_cooldown_seconds}s")
        self.voice_listener.start()
        self.speaker.start()
        asyncio.create_task(self.response_loop())

    async def event_message(self, message) -> None:
        if message.echo:
            return

        if message.content:
            await self.chat_queue.put((message.author.name, message.content))

        await self.handle_commands(message)

    async def response_loop(self) -> None:
        next_chat_reply_time = 0.0

        while True:
            try:
                mic_text = self.voice_queue.get_nowait()
            except queue.Empty:
                mic_text = None

            if mic_text is not None:
                if mic_text.startswith("[voice error]"):
                    print(mic_text)
                    continue

                print(f"Mic heard: {mic_text}")
                reply = await self.generate_reply(f"Streamer voice input: {mic_text}")
                channel = self.get_channel(self.settings.twitch_channel)
                if channel:
                    await channel.send(f"🎙️ {reply[:430]}")
                self.speaker.speak(reply)
                continue

            now = asyncio.get_running_loop().time()
            if now >= next_chat_reply_time:
                try:
                    author, content = self.chat_queue.get_nowait()
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0.1)
                    continue

                prompt = f"Twitch chat from {author}: {content}"
                reply = await self.generate_reply(prompt)
                channel = self.get_channel(self.settings.twitch_channel)
                if channel:
                    await channel.send(reply[:450])
                self.speaker.speak(reply)
                next_chat_reply_time = now + self.settings.chat_response_cooldown_seconds
                continue

            await asyncio.sleep(0.1)

    async def generate_reply(self, content: str) -> str:
        payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are CatVoice, a playful cat VTuber co-host. "
                        "Keep replies concise, Twitch-safe, and cat-like. "
                        "Use occasional cat words like meow, purr, paws, or hiss naturally, "
                        "without overdoing it."
                    ),
                },
                {"role": "user", "content": content},
            ],
            "options": {"num_predict": 120},
        }

        try:
            response = await asyncio.to_thread(
                requests.post,
                f"{self.settings.ollama_base_url}/api/chat",
                json=payload,
                timeout=self.settings.ollama_timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("message", {}).get("content", "").strip()
            return text or "Meow?"
        except requests.ReadTimeout:
            print("[ollama error] request timed out while waiting for model response")
            return (
                "Mrrp... that model is taking too long. "
                "Try increasing OLLAMA_TIMEOUT_SECONDS or using a smaller model."
            )
        except requests.RequestException as exc:
            print(f"[ollama error] {exc}")
            return "I couldn't reach Ollama. Is it running?"


async def main() -> None:
    settings = Settings.from_env()
    bot = CatVoiceBot(settings)
    try:
        await bot.start()
    finally:
        bot.voice_listener.stop()
        bot.speaker.stop()


if __name__ == "__main__":
    asyncio.run(main())
