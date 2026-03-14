# Anki Japanese TTS Generator

Automatically generates Japanese audio for your Anki flashcards using Azure Text-to-Speech (Keita neural voice). Reads exported Anki `.txt` files, generates `.mp3` files for the Full-Solution field, and outputs an updated `.txt` ready to re-import.

---

## Requirements

- Python 3.7+
- An Azure account with a Speech resource (free tier: 5M characters/month)

---

## Setup

### 1. Install the Azure SDK

```bash
python3 -m venv venv
pip install -r requirements.txt
# OR the SDK directly:
pip install azure-cognitiveservices-speech
```

### 2. Configure credentials

Copy the example env file and fill in your Azure details:

```bash
cp .env.example .env
```

Edit `.env`:

```
AZURE_SPEECH_KEY=your_key_here
AZURE_SPEECH_REGION=westeurope
INPUT_FOLDER=your input folder
OUTPUT_FOLDER=your output folder
```

**How to get your Azure Speech key:**

1. Go to [portal.azure.com](https://portal.azure.com) and sign in
2. Click **"Create a resource"** and search for **"Speech"**
3. Click **Speech** → **Create**
4. Fill in the form:
   - **Subscription**: your subscription
   - **Resource group**: create new or use existing
   - **Region**: pick one close to you (e.g. `West Europe`) — note this down
   - **Name**: anything you like
   - **Pricing tier**: **Free F0** (5M characters/month, no credit card needed)
5. Click **Review + Create** → **Create**
6. Once deployed, open the resource and click **Keys and Endpoint** in the left sidebar
7. Copy **Key 1** — that's your `AZURE_SPEECH_KEY`
8. The **Region** value is shown on the same page — use the short programmatic form e.g. `westeurope`, not the display name `West Europe`

---

## Usage

### Step 1 — Export from Anki

1. Open Anki and go to **File → Export**
2. Set **Export format** to **Notes in Plain Text (.txt)**
3. Set **Include** to the deck you want to add audio to
4. ✅ Check **"Include unique identifier"** — this is critical, it allows Anki to match rows back to existing cards on re-import instead of creating duplicates
5. ✅ Check **"Include HTML and media references"** — this preserves `[sound:...]` tags so the script can detect cards that already have audio and skip them
6. Click **Export** and save the file into your `INPUT_FOLDER`

### Step 2 — Run the script

Drop the exported `.txt` into your `INPUT_FOLDER`, then run:

```bash
python3 anki_tts.py
```

The script will generate one `.mp3` per card and write an updated `.txt` with the Audio field populated.

### Step 3 — Copy MP3s to Anki media folder

| Platform | Path |
|----------|------|
| Mac      | `~/Library/Application Support/Anki2/<Profile>/collection.media/` |
| Windows  | `%APPDATA%\Anki2\<Profile>\collection.media\` |
| Linux    | `~/.local/share/Anki2/<Profile>/collection.media/` |

Copy all `.mp3` files from `OUTPUT_FOLDER` into the media folder above.

### Step 4 — Import back into Anki

1. In Anki: **File → Import**
2. Select the updated `.txt` file from your `OUTPUT_FOLDER`
3. In the import dialog:
   - **Type**: should match your note type
   - **Deck**: select the correct deck
   - **Existing notes**: set to **"Update existing notes when first field matches"** — this updates your cards rather than creating duplicates
   - Make sure fields are mapped correctly (they should be automatic)
4. Click **Import**

### Step 5 — Verify

**Tools → Check Media** — Anki will confirm all audio files are found.

---

## Notes

- **Idempotent** — cards are skipped if the Audio field already contains a `[sound:...]` reference, or if the mp3 file already exists in the output folder. Safe to re-run.
- **No duplicates** — the unique identifier from the export ensures existing cards are updated, not duplicated.
- **Stable filenames** — MP3s are named by a hash of the sentence text, so the same sentence always produces the same file.
- **HTML stripped** — any HTML tags in the Full-Solution field are removed before sending to Azure.

---

## Git

`.env` and `.mp3` files are excluded via `.gitignore`. Commit `.env.example` as a template for others (or your future self).
