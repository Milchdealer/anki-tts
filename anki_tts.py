#!/usr/bin/env python3
"""
Anki Azure TTS Generator
Reads a tab-separated Anki import file, generates Japanese TTS audio
for the Full-Solution field using Azure TTS (Keita voice), and outputs
an updated .txt file with the Audio field populated.

Setup:
    pip install azure-cognitiveservices-speech

Configuration:
    Edit the CONFIG section below before running.
"""

import os
import re
import sys
import hashlib
from pathlib import Path


def load_env(env_path: str = ".env"):
    """Minimal .env loader — no extra dependencies needed."""
    path = Path(env_path)
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


load_env()  # loads .env from current working directory

# ── CONFIG ──────────────────────────────────────────────────────────────────
AZURE_SPEECH_KEY    = os.environ.get("AZURE_SPEECH_KEY", "")
AZURE_SPEECH_REGION = os.environ.get("AZURE_SPEECH_REGION", "")

INPUT_FOLDER  = os.environ.get("INPUT_FODLER", "input")         # folder with .txt card files
OUTPUT_FOLDER = os.environ.get("OUTPUT_FOLDER", "output")  # where updated .txt + mp3s go

VOICE_NAME = os.environ.get("VOICE_NAME", "ja-JP-KeitaNeural")

# Field order in your tab-separated file (0-indexed)
# Prompt, Context, Image-Front, Answer, Furigana, Full-Solution, Image-Back, Audio
FIELD_FULL_SOLUTION = 6
FIELD_AUDIO         = 8
TOTAL_FIELDS        = 10
# ────────────────────────────────────────────────────────────────────────────


def strip_html(text: str) -> str:
    """Remove HTML tags for TTS input."""
    return re.sub(r"<[^>]+>", "", text).strip()


def generate_audio(text: str, output_path: str) -> bool:
    """Generate TTS audio file using Azure. Returns True on success."""
    try:
        import azure.cognitiveservices.speech as speechsdk
    except ImportError:
        print("ERROR: azure-cognitiveservices-speech not installed.")
        print("Run: pip install azure-cognitiveservices-speech")
        sys.exit(1)

    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SPEECH_REGION
    )
    speech_config.speech_synthesis_voice_name = VOICE_NAME
    # Use 48kHz 192kbps MP3 — widely compatible including iOS AVAudioPlayer
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio48Khz192KBitRateMonoMp3
    )

    audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
    synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config,
        audio_config=audio_config
    )

    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        return True
    else:
        cancellation = result.cancellation_details
        print(f"  TTS failed: {cancellation.reason} — {cancellation.error_details}")
        return False


def process_file(input_path: str, output_folder: str):
    filename = os.path.basename(input_path)
    output_txt = os.path.join(output_folder, filename)
    os.makedirs(output_folder, exist_ok=True)

    updated_lines = []
    skipped = 0
    generated = 0
    already_done = 0

    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        # Pass through comment/tag lines unchanged
        stripped = line.strip()
        if stripped.startswith("#") or stripped == "":
            updated_lines.append(line)
            continue

        fields = stripped.split("\t")

        # Pad to expected field count if needed
        while len(fields) < TOTAL_FIELDS:
            fields.append("")

        full_solution = fields[FIELD_FULL_SOLUTION]
        audio_field   = fields[FIELD_AUDIO]

        # Skip if audio already exists
        if audio_field.strip():
            already_done += 1
            updated_lines.append(line)
            continue

        clean_text = strip_html(full_solution)
        if not clean_text:
            skipped += 1
            updated_lines.append(line)
            continue

        # Create a stable filename from the text content
        hash_id  = hashlib.md5(clean_text.encode("utf-8")).hexdigest()[:10]
        mp3_name = f"anki_tts_{hash_id}.mp3"
        mp3_path = os.path.join(output_folder, mp3_name)

        print(f"  Generating: {clean_text[:50]}...")

        if generate_audio(clean_text, mp3_path):
            fields[FIELD_AUDIO] = f"[sound:{mp3_name}]"
            generated += 1
        else:
            skipped += 1

        updated_lines.append("\t".join(fields) + "\n")

    with open(output_txt, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)

    print(f"\n  ✓ Done: {generated} generated, {already_done} skipped (already had audio), {skipped} skipped (no text)")
    print(f"  Output: {output_txt}")
    print(f"  MP3s:   {output_folder}")


def main():
    if not AZURE_SPEECH_KEY or not AZURE_SPEECH_REGION:
        print("ERROR: AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be set in your .env file.")
        print("Copy .env.example to .env and fill in your values.")
        sys.exit(1)

    if not os.path.isdir(INPUT_FOLDER):
        print(f"ERROR: INPUT_FOLDER not found: {INPUT_FOLDER}")
        sys.exit(1)

    txt_files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(".txt")]

    if not txt_files:
        print(f"No .txt files found in {INPUT_FOLDER}")
        sys.exit(0)

    print(f"Found {len(txt_files)} file(s) in {INPUT_FOLDER}\n")

    for txt_file in txt_files:
        full_path = os.path.join(INPUT_FOLDER, txt_file)
        print(f"Processing: {txt_file}")
        process_file(full_path, OUTPUT_FOLDER)


if __name__ == "__main__":
    main()
