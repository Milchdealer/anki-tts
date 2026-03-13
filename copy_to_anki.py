#!/usr/bin/env python3
"""
Copies generated TTS mp3 files from the output folder into Anki's
collection.media directory.

Works on macOS, Linux (including Manjaro), and Windows.
Auto-detects Anki's media folder; use --profile to specify a non-default profile.

Usage:
    python copy_to_anki.py                    # uses "User 1" profile
    python copy_to_anki.py --profile MyProfile
    python copy_to_anki.py --output other_dir  # custom output folder
    python copy_to_anki.py --dry-run           # preview without copying
"""

import argparse
import os
import platform
import shutil
import sys
from pathlib import Path

DEFAULT_PROFILE = "User 1"
DEFAULT_OUTPUT = "output"


def get_anki_base() -> Path:
    """Return the Anki2 base directory for the current OS."""
    system = platform.system()
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Anki2"
    elif system == "Linux":
        return Path.home() / ".local" / "share" / "Anki2"
    elif system == "Windows":
        appdata = Path(os.environ.get("APPDATA", ""))
        if not appdata.is_dir():
            print("ERROR: Could not determine APPDATA directory.")
            sys.exit(1)
        return appdata / "Anki2"
    else:
        print(f"ERROR: Unsupported platform: {system}")
        sys.exit(1)


def get_media_dir(profile: str) -> Path:
    base = get_anki_base()
    media = base / profile / "collection.media"
    if not media.is_dir():
        print(f"ERROR: Anki media folder not found: {media}")
        print(f"Available profiles: {', '.join(p.name for p in base.iterdir() if (p / 'collection.media').is_dir()) if base.is_dir() else 'N/A'}")
        sys.exit(1)
    return media


def main():
    parser = argparse.ArgumentParser(description="Copy TTS mp3s into Anki's media folder.")
    parser.add_argument("--profile", default=DEFAULT_PROFILE, help=f"Anki profile name (default: '{DEFAULT_PROFILE}')")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help=f"Source folder with mp3 files (default: '{DEFAULT_OUTPUT}')")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be copied without copying")
    args = parser.parse_args()

    output_dir = Path(args.output)
    if not output_dir.is_dir():
        print(f"ERROR: Output folder not found: {output_dir}")
        sys.exit(1)

    mp3s = sorted(output_dir.glob("*.mp3"))
    if not mp3s:
        print(f"No mp3 files found in {output_dir}")
        sys.exit(0)

    media_dir = get_media_dir(args.profile)
    print(f"Source:      {output_dir.resolve()}")
    print(f"Destination: {media_dir}")
    print(f"Files:       {len(mp3s)}")
    print()

    copied = 0
    skipped = 0
    for mp3 in mp3s:
        dest = media_dir / mp3.name
        if dest.exists() and dest.stat().st_size == mp3.stat().st_size:
            skipped += 1
            continue
        if args.dry_run:
            print(f"  [dry-run] {mp3.name}")
        else:
            shutil.copy2(mp3, dest)
        copied += 1

    action = "Would copy" if args.dry_run else "Copied"
    print(f"{action} {copied} file(s), skipped {skipped} (already present).")


if __name__ == "__main__":
    main()
