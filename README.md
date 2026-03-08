# CatVoice Twitch Bot

A Python Twitch bot that:
- Reads Twitch chat messages
- Listens to your microphone
- Generates responses with an OpenAI large language model
- Speaks responses out loud with text-to-speech

## 1) Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` values into your environment (or use a dotenv loader in your own workflow):

```bash
export TWITCH_TOKEN="oauth:..."
export TWITCH_CLIENT_ID="..."
export TWITCH_NICK="..."
export TWITCH_CHANNEL="..."
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4o-mini"
```

## 2) Run

```bash
python bot.py
```

## Notes

- `PyAudio` may require OS packages:
  - Ubuntu/Debian: `sudo apt install portaudio19-dev`
  - macOS: `brew install portaudio`
- Chat responses are posted to Twitch and spoken locally.
- Voice input is transcribed with Google Speech Recognition backend used by `SpeechRecognition`.
