# CatVoice Twitch Bot (Windows-Friendly + Free Local AI)

This app can:
- Read Twitch chat
- Listen to your microphone
- Prioritize your microphone when generating responses
- Reply to Twitch chat on a cooldown so it does not answer every single message
- Stores chat memory logs (excluding Shoku_Cyn) and uses recent memory for better context
- Randomly says off-topic cat/stream/get-to-know-you lines every 1–12 minutes
- Generate playful cat-like responses with a **free local AI model** (Ollama)
- Speak replies out loud with a realistic male local neural voice (slightly higher pitched) by default

---

## What you need before starting

1. **Windows 10/11**
2. **A Twitch account** (for the bot)
3. **Python 3.10+** from [python.org](https://www.python.org/downloads/windows/)
   - During install, check **"Add Python to PATH"**
4. **Ollama** from https://ollama.com/download/windows

---

## Step 1) Open this project in PowerShell

1. Open the project folder in File Explorer.
2. Click the path bar, type `powershell`, press Enter.

---

## Step 2) Install dependencies

Run these commands in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If activation is blocked, run once:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

---

## Step 3) Install and prepare Ollama

```powershell
ollama pull llama3.2:3b
```

Keep Ollama running while using the bot.

---

## Step 4) Get Twitch credentials

You need:
- `TWITCH_TOKEN`
- `TWITCH_CLIENT_ID`
- `TWITCH_NICK`
- `TWITCH_CHANNEL`

Easy source: https://twitchtokengenerator.com/
- Generate a chat bot token
- Copy Access Token (`oauth:...`) and Client ID

---

## Step 5) Make variables persistent (recommended)

Use a `.env` file so values are saved and reused every run.

### 5a) Create `.env` from the example

```powershell
Copy-Item .env.example .env
notepad .env
```

### 5b) Fill in `.env` values

Set these in Notepad:
- `TWITCH_TOKEN=oauth:...`
- `TWITCH_CLIENT_ID=...`
- `TWITCH_NICK=...`
- `TWITCH_CHANNEL=...`
- Keep `OLLAMA_BASE_URL=http://127.0.0.1:11434`
- Keep or change `OLLAMA_MODEL=llama3.2:3b`
- `OLLAMA_TIMEOUT_SECONDS=120` (increase this if first reply times out)
- `CHAT_RESPONSE_COOLDOWN_SECONDS=20` (how often to reply to chat; mic still takes priority)
- `OFFTOPIC_MIN_SECONDS=60`
- `OFFTOPIC_MAX_SECONDS=720`
- `MIC_AMBIENT_ADJUST_SECONDS=2.0`
- `MIC_LISTEN_TIMEOUT_SECONDS=3.0`
- `MIC_PHRASE_TIME_LIMIT_SECONDS=12.0`
- `MEMORY_DIR=memory` (folder where user chat logs are stored)
- `MEMORY_EXCLUDED_USER=` (leave blank to remember everyone, including Shoku_Cyn)
- `MEMORY_MAX_LINES=12` (how many recent memory lines to pass into model context)
- `USE_WEB_TTS=false` (recommended; uses local neural voice mode)
- `LOCAL_TTS_VOICE=en-US-GuyNeural` (realistic male default voice)
- `LOCAL_TTS_RATE=+10%`
- `LOCAL_TTS_PITCH=+4Hz` (slightly higher-pitched male voice)
- `STREAMLABS_TTS_URL=https://streamlabs.com/polly/speak`
- `STREAMLABS_VOICE=Joanna` (used when `USE_WEB_TTS=true`)
- `STREAMLABS_TTS_TIMEOUT_SECONDS=30`
- `STREAMELEMENTS_TTS_URL=` (optional fallback endpoint if `USE_WEB_TTS=true`)
- `STREAMELEMENTS_VOICE=Joanna` (used only if fallback URL is set)

Save and close Notepad.

That’s it — the bot now loads these automatically on startup.

> Optional alternative: use `setx` to store variables in Windows user environment, but `.env` is easier to edit.

---

## Step 6) Run the bot

```powershell
python bot.py
```

If startup is successful, it should connect to Twitch chat and start listening to your microphone.

---

## Daily quick start

```powershell
cd path\to\catvoice
.\.venv\Scripts\Activate.ps1
python bot.py
```

No need to retype variables if your `.env` file is already configured.

---

## Common Windows issues

### "python is not recognized"
- Reinstall Python and check **"Add Python to PATH"**.
- Reopen PowerShell.

### "ollama is not recognized"
- Restart PowerShell after installing Ollama.
- If still failing, restart Windows.

### "I couldn't reach Ollama. Is it running?"
- Open/start Ollama.
- Test:

```powershell
ollama list
```

### Read timed out on first message
- Bigger models can take longer for the first response.
- Increase `OLLAMA_TIMEOUT_SECONDS` in your `.env` (example: `180` or `240`).

### Too many chat replies / too few chat replies
- Change `CHAT_RESPONSE_COOLDOWN_SECONDS` in `.env`.
- Lower value = replies more often, higher value = replies less often.

### Chat replies cut off mid sentence
- The bot now trims long replies at sentence boundaries when possible before sending to Twitch.

### Too much / too little off-topic chatter
- Tune `OFFTOPIC_MIN_SECONDS` and `OFFTOPIC_MAX_SECONDS` in `.env`.
- Lower values = more frequent random lines, higher values = less frequent.

### Memory logs
- Logs are written per-user inside `MEMORY_DIR` (default `memory/`).
- If `MEMORY_EXCLUDED_USER` is blank, all users (including Shoku_Cyn) are remembered.
- Increase `MEMORY_MAX_LINES` if you want more context included in replies.

### TTS only speaks once / unreliable web voice
- Keep `USE_WEB_TTS=false` for the most reliable behavior (local neural TTS every message).
- Try another `LOCAL_TTS_VOICE` if you want a different realistic voice.
- If you enable web mode, Streamlabs/StreamElements may rate-limit or block requests.
- Increase `STREAMLABS_TTS_TIMEOUT_SECONDS` and try again.

### Mic misses words / cuts you off
- Increase `MIC_PHRASE_TIME_LIMIT_SECONDS` (example: `15` or `20`).
- Increase `MIC_AMBIENT_ADJUST_SECONDS` if your room is noisy.
- Increase `MIC_LISTEN_TIMEOUT_SECONDS` if you pause before speaking.

### Microphone not detected
- Windows Settings → Privacy & security → Microphone.
- Enable microphone access.

### Twitch auth errors
- Token must start with `oauth:`
- `TWITCH_NICK` should match token account.
