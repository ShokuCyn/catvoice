import asyncio
import os
import queue
import random
import re
import tempfile
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pyttsx3
import requests
import edge_tts
import speech_recognition as sr
from dotenv import load_dotenv
from playsound import playsound
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
    streamlabs_tts_url: str = "https://streamlabs.com/polly/speak"
    streamlabs_voice: str = "Joanna"
    streamlabs_tts_timeout_seconds: int = 30
    streamelements_tts_url: str = ""
    streamelements_voice: str = "Joanna"
    use_web_tts: bool = False
    local_tts_voice: str = "en-US-GuyNeural"
    local_tts_rate: str = "+25%"
    local_tts_pitch: str = "+10Hz"
    off_topic_min_seconds: int = 60
    off_topic_max_seconds: int = 720
    mic_ambient_adjust_seconds: float = 2.0
    mic_listen_timeout_seconds: float = 3.0
    mic_phrase_time_limit_seconds: float = 12.0
    memory_dir: str = "memory"
    memory_excluded_user: str = ""
    memory_max_lines: int = 0
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
        tts_timeout_raw = os.getenv("STREAMLABS_TTS_TIMEOUT_SECONDS", "30")
        off_topic_min_raw = os.getenv("OFFTOPIC_MIN_SECONDS", "60")
        off_topic_max_raw = os.getenv("OFFTOPIC_MAX_SECONDS", "720")
        mic_ambient_adjust_raw = os.getenv("MIC_AMBIENT_ADJUST_SECONDS", "2.0")
        mic_listen_timeout_raw = os.getenv("MIC_LISTEN_TIMEOUT_SECONDS", "3.0")
        mic_phrase_limit_raw = os.getenv("MIC_PHRASE_TIME_LIMIT_SECONDS", "12.0")
        memory_max_lines_raw = os.getenv("MEMORY_MAX_LINES", "0")

        try:
            timeout_seconds = max(15, int(timeout_raw))
        except ValueError:
            timeout_seconds = 120

        try:
            cooldown_seconds = max(0, int(cooldown_raw))
        except ValueError:
            cooldown_seconds = 20

        try:
            tts_timeout_seconds = max(5, int(tts_timeout_raw))
        except ValueError:
            tts_timeout_seconds = 30

        try:
            off_topic_min_seconds = max(60, int(off_topic_min_raw))
        except ValueError:
            off_topic_min_seconds = 60

        try:
            off_topic_max_seconds = max(off_topic_min_seconds, int(off_topic_max_raw))
        except ValueError:
            off_topic_max_seconds = 720
        try:
            mic_ambient_adjust_seconds = max(0.5, float(mic_ambient_adjust_raw))
        except ValueError:
            mic_ambient_adjust_seconds = 2.0

        try:
            mic_listen_timeout_seconds = max(1.0, float(mic_listen_timeout_raw))
        except ValueError:
            mic_listen_timeout_seconds = 3.0

        try:
            mic_phrase_time_limit_seconds = max(3.0, float(mic_phrase_limit_raw))
        except ValueError:
            mic_phrase_time_limit_seconds = 12.0

        try:
            memory_max_lines = int(memory_max_lines_raw)
        except ValueError:
            memory_max_lines = 0

        use_web_tts = os.getenv("USE_WEB_TTS", "false").strip().lower() in {"1", "true", "yes", "on"}

        return Settings(
            twitch_token=required["TWITCH_TOKEN"],
            twitch_client_id=required["TWITCH_CLIENT_ID"],
            twitch_nick=required["TWITCH_NICK"],
            twitch_channel=required["TWITCH_CHANNEL"],
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            ollama_timeout_seconds=timeout_seconds,
            chat_response_cooldown_seconds=cooldown_seconds,
            streamlabs_tts_url=os.getenv("STREAMLABS_TTS_URL", "https://streamlabs.com/polly/speak"),
            streamlabs_voice=os.getenv("STREAMLABS_VOICE", "Joanna"),
            streamlabs_tts_timeout_seconds=tts_timeout_seconds,
            streamelements_tts_url=os.getenv("STREAMELEMENTS_TTS_URL", "").strip(),
            streamelements_voice=os.getenv("STREAMELEMENTS_VOICE", "Joanna"),
            use_web_tts=use_web_tts,
            local_tts_voice=os.getenv("LOCAL_TTS_VOICE", "en-US-GuyNeural"),
            local_tts_rate=os.getenv("LOCAL_TTS_RATE", "+20%"),
            local_tts_pitch=os.getenv("LOCAL_TTS_PITCH", "+10Hz"),
            off_topic_min_seconds=off_topic_min_seconds,
            off_topic_max_seconds=off_topic_max_seconds,
            mic_ambient_adjust_seconds=mic_ambient_adjust_seconds,
            mic_listen_timeout_seconds=mic_listen_timeout_seconds,
            mic_phrase_time_limit_seconds=mic_phrase_time_limit_seconds,
            memory_dir=os.getenv("MEMORY_DIR", "memory"),
            memory_excluded_user=os.getenv("MEMORY_EXCLUDED_USER", "").strip(),
            memory_max_lines=memory_max_lines,
            bot_prefix=os.getenv("BOT_PREFIX", "!"),
        )


class VoiceListener(threading.Thread):
    def __init__(self, out_queue: queue.Queue[str], settings: Settings) -> None:
        super().__init__(daemon=True)
        self.out_queue = out_queue
        self.recognizer = sr.Recognizer()
        self.settings = settings
        self._stop = threading.Event()

    def run(self) -> None:
        mic = sr.Microphone()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.recognizer.non_speaking_duration = 0.5

        with mic as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=self.settings.mic_ambient_adjust_seconds)

        while not self._stop.is_set():
            try:
                with mic as source:
                    audio = self.recognizer.listen(
                        source,
                        timeout=self.settings.mic_listen_timeout_seconds,
                        phrase_time_limit=self.settings.mic_phrase_time_limit_seconds,
                    )
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
    def __init__(self, settings: Settings) -> None:
        super().__init__(daemon=True)
        self.settings = settings
        self._stop_sentinel = object()
        self.queue: queue.Queue[object] = queue.Queue()
        self._stop = threading.Event()

    def run(self) -> None:
        while not self._stop.is_set():
            item = self.queue.get()
            if item is self._stop_sentinel:
                break
            if not isinstance(item, tuple) or len(item) != 2:
                continue

            text, force_local_default = item
            if not isinstance(text, str):
                continue

            try:
                self._speak(text, force_local_default=bool(force_local_default))
            except Exception as exc:  # noqa: BLE001
                # Never let the speaker worker die; keep consuming queue items.
                print(f"[speaker worker error] {exc}")

    def speak(self, text: str, force_local_default: bool = False) -> None:
        self.queue.put((text, force_local_default))

    def stop(self) -> None:
        self._stop.set()
        self.queue.put(self._stop_sentinel)

    def _speak(self, text: str, force_local_default: bool = False) -> None:
        if self.settings.use_web_tts and not force_local_default:
            self._speak_streamlabs(text)
            return

        safe_text = self._normalize_tts_text(text)
        if safe_text:
            self._speak_local_neural(safe_text)

    def _speak_streamlabs(self, text: str) -> None:
        safe_text = self._normalize_tts_text(text)
        if not safe_text:
            return

        try:
            audio_bytes = self._fetch_streamlabs_audio(safe_text)
        except requests.RequestException as exc:
            if not self.settings.streamelements_tts_url:
                print(f"[streamlabs tts error] {exc}; using local fallback voice")
                self._speak_local_fallback(safe_text)
                return
            print(f"[streamlabs tts error] {exc}; trying StreamElements fallback")
            try:
                audio_bytes = self._fetch_streamelements_audio(safe_text)
            except requests.RequestException as fallback_exc:
                print(f"[streamelements tts error] {fallback_exc}; using local fallback voice")
                self._speak_local_fallback(safe_text)
                return

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
                audio_file.write(audio_bytes)
                temp_path = Path(audio_file.name)
            try:
                playsound(str(temp_path), block=True)
            finally:
                temp_path.unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[tts playback error] {exc}; using local fallback voice")
            self._speak_local_fallback(safe_text)

    def _normalize_tts_text(self, text: str) -> str:
        cleaned = text.replace("*", "")
        cleaned = " ".join(cleaned.split())
        return cleaned[:280]

    def _speak_local_neural(self, text: str) -> None:
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_file:
                temp_path = Path(audio_file.name)

            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=self.settings.local_tts_voice,
                    rate=self.settings.local_tts_rate,
                    pitch=self.settings.local_tts_pitch,
                )
                asyncio.run(communicate.save(str(temp_path)))
                playsound(str(temp_path), block=True)
            finally:
                temp_path.unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[local neural tts error] {exc}; using pyttsx3 fallback")
            self._speak_local_fallback(text)

    def _speak_local_fallback(self, text: str) -> None:
        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", 195)
            engine.setProperty("volume", 1.0)
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as exc:  # noqa: BLE001
            print(f"[local tts fallback error] {exc}")

    def _fetch_streamlabs_audio(self, text: str) -> bytes:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json,audio/mpeg,*/*",
            "Referer": "https://streamlabs.com/",
        }
        response = requests.get(
            self.settings.streamlabs_tts_url,
            params={"voice": self.settings.streamlabs_voice, "text": text},
            headers=headers,
            timeout=self.settings.streamlabs_tts_timeout_seconds,
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if content_type.startswith("audio/"):
            return response.content

        body = response.text.strip()
        if body.startswith("http://") or body.startswith("https://"):
            audio_response = requests.get(body, timeout=self.settings.streamlabs_tts_timeout_seconds)
            audio_response.raise_for_status()
            return audio_response.content

        try:
            data = response.json()
        except ValueError as exc:
            snippet = body[:140].replace("\n", " ")
            raise requests.RequestException(f"Streamlabs returned non-JSON response: {snippet}") from exc

        speak_url = data.get("speak_url")
        if not speak_url:
            raise requests.RequestException(f"unexpected Streamlabs response: {data}")

        audio_response = requests.get(speak_url, timeout=self.settings.streamlabs_tts_timeout_seconds)
        audio_response.raise_for_status()
        return audio_response.content

    def _fetch_streamelements_audio(self, text: str) -> bytes:
        response = requests.get(
            self.settings.streamelements_tts_url,
            params={"voice": self.settings.streamelements_voice, "text": text},
            timeout=self.settings.streamlabs_tts_timeout_seconds,
        )
        response.raise_for_status()
        return response.content


class TiuCynBot(commands.Bot):
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
        self.voice_listener = VoiceListener(self.voice_queue, settings)
        self.speaker = Speaker(settings)
        self.memory_dir = Path(self.settings.memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_speaker_running(self) -> None:
        if not self.speaker.is_alive():
            print("[speaker] worker stopped unexpectedly; restarting")
            self.speaker = Speaker(self.settings)
            self.speaker.start()

    async def event_ready(self) -> None:
        print(f"Logged in as: {self.nick}")
        print(f"Listening in: #{self.settings.twitch_channel}")
        print(f"Chat response cooldown: {self.settings.chat_response_cooldown_seconds}s")
        self.voice_listener.start()
        self.speaker.start()
        asyncio.create_task(self.response_loop())

    def _next_off_topic_delay(self) -> float:
        return random.uniform(
            float(self.settings.off_topic_min_seconds),
            float(self.settings.off_topic_max_seconds),
        )

    def _random_off_topic_prompt(self) -> str:
        prompts = [
            "Say one short, playful cat-themed thought unrelated to current chat.",
            "Ask the streamer one fun personal question to get to know them better.",
            "Say a cute off-topic line about snacks, naps, or cat energy on stream.",
            "Ask the audience a short question about their favorite part of today.",
            "Drop a random wholesome cat fact in one sentence.",
            "Ask the streamer about their mood, favorite game, or current vibe.",
        ]
        return random.choice(prompts)

    def _fit_for_chat(self, text: str, max_chars: int) -> str:
        if len(text) <= max_chars:
            return text

        clipped = text[:max_chars].rstrip()
        sentence_break = max(clipped.rfind('. '), clipped.rfind('! '), clipped.rfind('? '))
        if sentence_break >= int(max_chars * 0.6):
            return clipped[: sentence_break + 1].rstrip()

        last_space = clipped.rfind(' ')
        if last_space >= int(max_chars * 0.6):
            return clipped[:last_space].rstrip() + '…'

        return clipped.rstrip() + '…'

    def _memory_file_for_user(self, username: str) -> Path:
        safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in username)
        return self.memory_dir / f"{safe.lower()}.log"

    def _append_user_memory(self, username: str, content: str) -> None:
        if not content.strip():
            return
        if self.settings.memory_excluded_user and username.casefold() == self.settings.memory_excluded_user.casefold():
            return

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        line = f"[{timestamp}] {username}: {content.strip()}\n"
        memory_path = self._memory_file_for_user(username)
        with memory_path.open("a", encoding="utf-8") as f:
            f.write(line)

    def _recent_memory_context(self) -> str:
        lines: list[str] = []

        global_path = self.memory_dir / ".gitkeep"
        if global_path.exists():
            try:
                with global_path.open("r", encoding="utf-8") as f:
                    global_lines = [ln.strip() for ln in f.readlines() if ln.strip()]
                lines.extend(global_lines[-40:])
            except OSError:
                pass

        for path in sorted(self.memory_dir.glob("*.log")):
            try:
                with path.open("r", encoding="utf-8") as f:
                    user_lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            except OSError:
                continue

            if user_lines:
                lines.extend(user_lines[-2:])

        if not lines:
            return ""

        if self.settings.memory_max_lines > 0:
            lines = lines[-self.settings.memory_max_lines :]
        return "\n".join(lines)

    def _append_global_memory(self, username: str, content: str) -> None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        line = f"[{timestamp}] {username}: {content.strip()}\n"
        global_path = self.memory_dir / ".gitkeep"
        with global_path.open("a", encoding="utf-8") as f:
            f.write(line)

    def _append_bot_memory(self, content: str) -> None:
        if not content.strip():
            return
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        line = f"[{timestamp}] Tiu_Cyn: {content.strip()}\n"
        global_path = self.memory_dir / ".gitkeep"
        with global_path.open("a", encoding="utf-8") as f:
            f.write(line)

    def _log_bot_reply(self, reply: str) -> None:
        self._append_bot_memory(reply)

    async def event_message(self, message) -> None:

        if message.echo:
            return
        content = message.content or ""
        self._append_global_memory(message.author.name, content)
        self._append_user_memory(message.author.name, content)
        if content:
            await self.chat_queue.put((message.author.name, content))
        await self.handle_commands(message)

    async def response_loop(self) -> None:
        next_chat_reply_time = 0.0
        now = asyncio.get_running_loop().time()
        next_off_topic_time = now + self._next_off_topic_delay()

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
                    await channel.send(f"🎙️ {self._fit_for_chat(reply, 430)}")
                self._log_bot_reply(reply)
                self._ensure_speaker_running()
                self.speaker.speak(reply)
                continue

            now = asyncio.get_running_loop().time()
            if now >= next_off_topic_time:
                off_topic_prompt = self._random_off_topic_prompt()
                reply = await self.generate_reply(
                    f"Off-topic spontaneous line for stream: {off_topic_prompt}"
                )
                channel = self.get_channel(self.settings.twitch_channel)
                if channel:
                    await channel.send(f"🐾 {self._fit_for_chat(reply, 440)}")
                self._log_bot_reply(reply)
                self._ensure_speaker_running()
                self.speaker.speak(reply, force_local_default=True)
                next_off_topic_time = now + self._next_off_topic_delay()
                continue

            now = asyncio.get_running_loop().time()
            if now >= next_chat_reply_time:
                try:
                    author, content = self.chat_queue.get_nowait()
                except asyncio.QueueEmpty:
                    await asyncio.sleep(0.1)
                    continue
                reply = await self.generate_reply(f"Twitch chat from {author}: {content}")
                channel = self.get_channel(self.settings.twitch_channel)
                if channel:
                    await channel.send(self._fit_for_chat(reply, 450))
                self._log_bot_reply(reply)
                self._ensure_speaker_running()
                self.speaker.speak(reply)
                next_chat_reply_time = now + self.settings.chat_response_cooldown_seconds
                continue

            await asyncio.sleep(0.1)

    def _clean_reply_text(self, text: str) -> str:
        no_asterisk_actions = re.sub(r"\*[^*]+\*", "", text)
        no_asterisks = no_asterisk_actions.replace("*", "")
        normalized = " ".join(no_asterisks.split())
        return normalized.strip()

    def _build_user_prompt(self, content: str) -> str:
        memory = self._recent_memory_context()
        if not memory:
            return content

        return (
            "Current input:\n"
            f"{content}\n\n"
            "Recent memory log (users + bot):\n"
            f"{memory}\n\n"
            "Use memory only if relevant and keep response concise."
        )

    async def generate_reply(self, content: str) -> str:
        payload = {
            "model": self.settings.ollama_model,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Tiu_Cyn, a playful cat VTuber co-host. "
                        "Keep replies concise, Twitch-safe, and cat-like. "
                        "Use occasional cat words like meow, purr, paws, or hiss naturally, "
                        "without overdoing it. Keep replies short (1 sentence, <=20 words). Never give streaming advice unless explicitly asked. Never use roleplay/action formatting like *purrs* or stage directions."
                    ),
                },
                {"role": "user", "content": self._build_user_prompt(content)},
            ],
            "options": {"num_predict": 70},
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
            cleaned = self._clean_reply_text(text)
            return cleaned or "Meow?"
        except requests.ReadTimeout:
            print("[ollama error] request timed out while waiting for model response")
            return "Mrrp... that model is taking too long. Try increasing OLLAMA_TIMEOUT_SECONDS or using a smaller model."
        except requests.RequestException as exc:
            print(f"[ollama error] {exc}")
            return "I couldn't reach Ollama. Is it running?"


async def main() -> None:
    settings = Settings.from_env()
    bot = TiuCynBot(settings)
    try:
        await bot.start()
    finally:
        bot.voice_listener.stop()
        bot.speaker.stop()


if __name__ == "__main__":
    asyncio.run(main())
