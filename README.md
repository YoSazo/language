# Japanese Coach

Japanese Coach is a local-first Japanese conversation trainer:

- Your PC runs `Whisper` and `Ollama`.
- Your iPhone acts as the microphone, speaker, and study UI.
- You talk in Japanese, get a short Japanese reply back, and use quick actions when you need help.

This repo is designed for your setup:

- Windows PC running Ollama
- iPhone app installed through AltStore
- GitHub Actions producing an unsigned `.ipa` you can sideload

## What You Get

- `Conversation mode`: hold to talk, get short Japanese replies
- `How do I say this?`: speak English, get natural Japanese back
- `Shadow last line`: repeat the last AI sentence and get a pronunciation-style score
- `Explain last`: get a short English explanation only when you ask for it

## Architecture

```text
iPhone mic -> WebSocket -> Python backend -> Whisper -> Ollama -> iPhone UI/TTS
```

- The iPhone streams raw `16 kHz` PCM audio to the backend over local Wi-Fi.
- The backend transcribes speech with `faster-whisper`.
- Ollama generates the next Japanese tutor reply.
- The iPhone speaks the Japanese reply using built-in `AVSpeechSynthesizer` voices for lower latency.

## Backend Setup

1. Install Python packages:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\python -m pip install --upgrade pip
   .\.venv\Scripts\pip install -r backend\requirements.txt
   ```

2. Copy the sample env file:

   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```

3. Make sure Ollama is installed and running on your PC.

4. Pull a fast Japanese-capable model. Recommended:

   ```powershell
   ollama pull qwen2.5:7b
   ollama pull qwen3.5:0.8b
   ```

   If you do not pull `qwen2.5:7b`, the backend will try other installed models such as `gemma3:4b`.

5. Start the backend:

   ```powershell
   .\.venv\Scripts\python -m backend.main
   ```

6. Find your PC's LAN IP:

   ```powershell
   ipconfig
   ```

   Then use `YOUR_IP:8765` inside the iPhone app.

## iPhone App Build

The iOS app lives in [ios/JapaneseCoach/project.yml](ios/JapaneseCoach/project.yml). It uses `XcodeGen` so the GitHub runner can generate the Xcode project during CI.

### GitHub Actions

The workflow in [.github/workflows/ios-build.yml](.github/workflows/ios-build.yml):

- installs `xcodegen`
- generates the Xcode project
- builds an unsigned iPhone app
- packages it into a standard `.ipa`
- uploads the `.ipa` as a workflow artifact
- attaches the `.ipa` to tagged GitHub releases

### AltStore Flow

1. Push this repo to GitHub.
2. Run the `iOS Build` workflow or push a tag like `v0.1.0`.
3. Download the generated `.ipa`.
4. Install the `.ipa` with AltStore / AltServer.

There is an AltStore source template at [altstore/source.template.json](altstore/source.template.json) if you want update feeds later.

## Usage

1. Open the app on your iPhone.
2. Enter your PC's address, for example `192.168.1.42:8765`.
3. Tap `Connect`.
4. Hold the big button while speaking.
5. Release to send the turn.

Recommended flow for fast speaking practice:

- Stay in `Conversation`
- Use `Explain Last` only when needed
- Use `How Do I Say This` to rescue yourself without leaving immersion for long
- Use `Shadow Last Line` to drill rhythm and repeat important phrases

## Latency Notes

For your `RTX 3060 12 GB`, the fastest experience will usually come from:

- `WHISPER_MODEL_SIZE=small`
- `PREFERRED_CHAT_MODELS=qwen2.5:7b,gemma3:4b,qwen3.5:4b`
- keeping replies short

This is designed to feel like push-to-talk conversation, not fully simultaneous voice chat.

## Files

- [backend/app/server.py](backend/app/server.py): FastAPI + WebSocket server
- [backend/app/tutor.py](backend/app/tutor.py): Japanese tutoring logic
- [ios/JapaneseCoach/JapaneseCoach/Views/ContentView.swift](ios/JapaneseCoach/JapaneseCoach/Views/ContentView.swift): iPhone UI
- [.github/workflows/ios-build.yml](.github/workflows/ios-build.yml): CI build pipeline

