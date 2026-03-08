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

        return Settings(
            twitch_token=required["TWITCH_TOKEN"],
            twitch_client_id=required["TWITCH_CLIENT_ID"],
            twitch_nick=required["TWITCH_NICK"],
            twitch_channel=required["TWITCH_CHANNEL"],
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
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


class Speaker:
    def __init__(self) -> None:
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 185)

    def speak(self, text: str) -> None:
        self.engine.say(text)
        self.engine.runAndWait()


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
        self.voice_listener = VoiceListener(self.voice_queue)
        self.speaker = Speaker()

    async def event_ready(self) -> None:
        print(f"Logged in as: {self.nick}")
        print(f"Listening in: #{self.settings.twitch_channel}")
        self.voice_listener.start()
        asyncio.create_task(self.voice_loop())

    async def event_message(self, message) -> None:
        if message.echo:
            return

        if message.content:
            prompt = f"Twitch chat from {message.author.name}: {message.content}"
            reply = await self.generate_reply(prompt)
            await message.channel.send(reply[:450])
            await asyncio.to_thread(self.speaker.speak, reply)

        await self.handle_commands(message)

    async def voice_loop(self) -> None:
        while True:
            text = await asyncio.to_thread(self.voice_queue.get)
            if text.startswith("[voice error]"):
                print(text)
                continue
            print(f"Mic heard: {text}")
            reply = await self.generate_reply(f"Streamer voice input: {text}")
            channel = self.get_channel(self.settings.twitch_channel)
            if channel:
                await channel.send(f"🎙️ {reply[:430]}")
            await asyncio.to_thread(self.speaker.speak, reply)

    async def generate_reply(self, content: str) -> str:
        payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": "You are CatVoice, a friendly live-stream co-host. Keep replies concise, fun, and safe for Twitch.",
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
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("message", {}).get("content", "").strip()
            return text or "Meow?"
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


if __name__ == "__main__":
    asyncio.run(main())
