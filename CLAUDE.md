# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A tool that generates Japanese TTS audio (Azure, Keita neural voice) for Anki flashcards. Two scripts:

- **`anki_tts.py`** — Reads tab-separated Anki export `.txt` files from `input/`, generates `.mp3` per card via Azure TTS, writes updated `.txt` + mp3s to `output/`.
- **`copy_to_anki.py`** — Copies generated `.mp3` files from `output/` into Anki's `collection.media/` folder. Cross-platform (macOS/Linux/Windows). Auto-detects Anki path.

## Commands

```bash
# Setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Generate TTS audio
python3 anki_tts.py

# Copy mp3s to Anki (profile auto-detection shows available profiles on error)
python3 copy_to_anki.py --profile <ProfileName>
python3 copy_to_anki.py --profile <ProfileName> --dry-run
```

## Configuration

All config via `.env` (copy from `.env.example`):
- `AZURE_SPEECH_KEY` / `AZURE_SPEECH_REGION` — Azure Speech credentials
- `INPUT_FOLDER` / `OUTPUT_FOLDER` — override default `input/` and `output/` dirs
- `VOICE_NAME` — TTS voice (default: `ja-JP-KeitaNeural`)

## Key Design Decisions

- **Field mapping is hardcoded**: `anki_tts.py` expects a specific tab-separated field order (10 fields). `FIELD_FULL_SOLUTION=6` and `FIELD_AUDIO=8` are constants at the top of the file. Adjust these if the note type changes.
- **Stable filenames via content hash**: MP3s are named `anki_tts_{md5[:10]}.mp3` from the text content, making the process idempotent — same text always produces the same filename.
- **Idempotent**: Cards are skipped if the Audio field contains `[sound:...]` or if the mp3 already exists in the output folder.
- **ffmpeg for iOS compatibility**: Azure SDK outputs 48kHz raw MPEG frames without ID3 headers. iOS AnkiMobile rejects both the sample rate and missing headers. `anki_tts.py` auto-detects ffmpeg and re-encodes to 44.1kHz 128kbps mono. ffmpeg is optional but required for iOS playback.
- **No external dependencies beyond Azure SDK + ffmpeg**: The `.env` loader is hand-rolled to avoid extra deps.
