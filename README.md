# CatVoice Twitch Bot (Windows-Friendly + Free Local AI)

This is a small Python app that can act like your stream co-host. It can:
- Read Twitch chat
- Listen to your microphone
- Generate responses with a **free local AI model** (Ollama)
- Speak that response out loud on your PC

If you are on **Windows** and not super technical, follow this exactly.

---

## What you need before starting

1. **Windows 10/11**
2. **A Twitch account** (for the bot)
3. **Python 3.10+** installed from [python.org](https://www.python.org/downloads/windows/)
   - During install, check **"Add Python to PATH"**
4. **Ollama** (free local AI runtime) from https://ollama.com/download/windows

---

## Step 1) Download/open this project

If you already have the files, open the project folder in File Explorer.

Easy way to open a terminal in the folder:
1. Click the folder path bar in File Explorer
2. Type `powershell`
3. Press Enter

You should now have a PowerShell window in this project folder.

---

## Step 2) Create and activate a virtual environment

Run these commands one at a time in **PowerShell**:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run this once:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then run:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

## Step 3) Install and start Ollama (free chatbot API)

1. Install Ollama for Windows: https://ollama.com/download/windows
2. Open a **new** PowerShell window and run:

```powershell
ollama pull llama3.2:3b
```

That downloads a free model the bot can use.

> Keep Ollama running in the background while using the bot.

---

## Step 4) Get your Twitch bot credentials

You need values for:
- `TWITCH_TOKEN`
- `TWITCH_CLIENT_ID`
- `TWITCH_NICK`
- `TWITCH_CHANNEL`

### Easiest way for token + client ID
Use the Twitch Token Generator:
- https://twitchtokengenerator.com/

Generate a **chat bot token** and copy:
- **Access Token** (must look like `oauth:...`)
- **Client ID**

### What each value means
- `TWITCH_TOKEN`: your bot OAuth token, starts with `oauth:`
- `TWITCH_CLIENT_ID`: client id from token generator
- `TWITCH_NICK`: your bot Twitch username (lowercase recommended)
- `TWITCH_CHANNEL`: your channel name (the channel to join)

---

## Step 5) Set environment variables (PowerShell)

In the same PowerShell window, run (replace values with yours):

```powershell
$env:TWITCH_TOKEN="oauth:paste_yours_here"
$env:TWITCH_CLIENT_ID="paste_client_id_here"
$env:TWITCH_NICK="your_bot_username"
$env:TWITCH_CHANNEL="your_channel_name"
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
$env:OLLAMA_MODEL="llama3.2:3b"
```

> Important: these `$env:` values only last for the current terminal window.

---

## Step 6) Run the bot

```powershell
python bot.py
```

If it starts correctly, it should connect to Twitch chat and begin listening for microphone input.

---

## Daily use (quick start after first setup)

When you come back later:

```powershell
cd path\to\catvoice
.\.venv\Scripts\Activate.ps1
# make sure Ollama is running
# set env vars again (or use a .env loader in your own workflow)
python bot.py
```

---

## Common Windows issues

### "python is not recognized"
- Reinstall Python and check **"Add Python to PATH"** during setup.
- Reopen PowerShell after install.

### "ollama is not recognized"
- Restart PowerShell after installing Ollama.
- If still broken, restart Windows once and try again.

### "I couldn't reach Ollama. Is it running?"
- Start Ollama app on Windows.
- Test in PowerShell:

```powershell
ollama list
```

If that works, run the bot again.

### Microphone not detected
- Check Windows Privacy settings:
  - **Settings → Privacy & security → Microphone**
  - Make sure microphone access is enabled.

### No speech output
- Ensure Windows audio output is working.
- `pyttsx3` uses local system voices; try changing default Windows voice settings.

### Twitch auth errors
- Make sure token starts with `oauth:`
- Make sure `TWITCH_NICK` matches the account used for the token.

---

## Notes

- Chat responses are posted to Twitch and spoken locally on your machine.
- Voice input is transcribed using the SpeechRecognition package (Google Speech backend).
- If dependencies fail to install, upgrade pip first:

```powershell
python -m pip install --upgrade pip
```
