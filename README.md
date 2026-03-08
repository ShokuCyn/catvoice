# CatVoice Twitch Bot (Windows-Friendly + Free Local AI)

This app can:
- Read Twitch chat
- Listen to your microphone
- Generate playful cat-like responses with a **free local AI model** (Ollama)
- Speak replies out loud on your PC with a cuter/faster voice profile

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
ollama pull gpt-oss:20b
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
- Keep or change `OLLAMA_MODEL=gpt-oss:20b`

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

### Microphone not detected
- Windows Settings → Privacy & security → Microphone.
- Enable microphone access.

### Twitch auth errors
- Token must start with `oauth:`
- `TWITCH_NICK` should match token account.
