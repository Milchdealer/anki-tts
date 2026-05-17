"""
Converts non-Claude Japanese deck cards to Japanese Fill-in-the-Blank format.
- Active "3. All-Purpose Card" notes → converted in place
- Suspended cards + Basic/Minimal Pairs/Spellings/Mnemonics/Picture Words → moved to Archive deck
Run with Anki CLOSED.
"""
import sqlite3, shutil, os, sys, time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.expandvars(r'%APPDATA%\Anki2\Teraku\collection.anki2')
BACKUP_PATH = DB_PATH + f'.backup_convert_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
shutil.copy2(DB_PATH, BACKUP_PATH)
print(f'Backup: {BACKUP_PATH}')

conn = sqlite3.connect(DB_PATH)
conn.create_collation('unicase', lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower()))
cur = conn.cursor()

SEP = '\x1f'
TARGET_NOTETYPE_ID = 1769985345426  # Japanese Fill-in-the-Blank
CLAUDE_DECK_ID = 1773012065806

JAPANESE_DECK_IDS = (1738918480114, 1738918480115, 1716403620198,
                     1738918480116, 1769985523000)
ph = ','.join('?' * len(JAPANESE_DECK_IDS))

# ── Get notetype IDs ──────────────────────────────────────────────────────────
cur.execute("SELECT id, name FROM notetypes")
nt_map = {name: nid for nid, name in cur.fetchall()}
print('\nNotetypes found:', list(nt_map.keys()))

ALL_PURPOSE_ID   = nt_map.get('3. All-Purpose Card')
BASIC_ID         = nt_map.get('Basic')
MINIMAL_PAIRS_ID = nt_map.get('1. Minimal Pairs')
SPELLINGS_ID     = nt_map.get('1. Spellings and Sounds')
MNEMONICS_ID     = nt_map.get('2. Mnemonics')
PICTURE_WORDS_ID = nt_map.get('2. Picture Words')

ARCHIVE_NOTETYPES = {nid for nid in [
    BASIC_ID, MINIMAL_PAIRS_ID, SPELLINGS_ID, MNEMONICS_ID, PICTURE_WORDS_ID
] if nid}

# ── Create Archive deck if it doesn't exist ───────────────────────────────────
cur.execute("SELECT id FROM decks WHERE name = 'Archive'")
row = cur.fetchone()
if row:
    ARCHIVE_DECK_ID = row[0]
    print(f'\nArchive deck already exists: {ARCHIVE_DECK_ID}')
else:
    # Copy blob fields from Default deck (id=1) to avoid constructing protobuf manually
    cur.execute("SELECT common, kind FROM decks WHERE id = 1")
    default_common, default_kind = cur.fetchone()
    ARCHIVE_DECK_ID = int(time.time() * 1000)
    time.sleep(0.002)
    cur.execute("""INSERT INTO decks (id, name, mtime_secs, usn, common, kind)
        VALUES (?, 'Archive', ?, -1, ?, ?)""",
        (ARCHIVE_DECK_ID, int(time.time()), default_common, default_kind))
    print(f'\nCreated Archive deck: {ARCHIVE_DECK_ID}')

# ── Collect card IDs to archive ───────────────────────────────────────────────
# 1. All suspended cards in Japanese decks
cur.execute(f"""SELECT c.id, c.nid FROM cards c
    JOIN notes n ON c.nid = n.id
    WHERE c.did IN ({ph}) AND c.queue = -1""", JAPANESE_DECK_IDS)
suspended_cards = cur.fetchall()

# 2. Active cards with archive note types in Japanese decks
cur.execute(f"""SELECT c.id, c.nid FROM cards c
    JOIN notes n ON c.nid = n.id
    WHERE c.did IN ({ph}) AND n.mid IN ({','.join('?' * len(ARCHIVE_NOTETYPES))})
    AND c.queue != -1""", list(JAPANESE_DECK_IDS) + list(ARCHIVE_NOTETYPES))
archive_notetype_cards = cur.fetchall()

all_archive = list({cid: nid for cid, nid in suspended_cards + archive_notetype_cards}.items())
print(f'\nCards to archive: {len(all_archive)} '
      f'({len(suspended_cards)} suspended + {len(archive_notetype_cards)} archive notetypes)')

# Move to Archive deck
archived_count = 0
for cid, nid in all_archive:
    cur.execute("UPDATE cards SET did = ?, mod = ? WHERE id = ?",
                (ARCHIVE_DECK_ID, int(time.time()), cid))
    archived_count += 1
print(f'  Moved {archived_count} cards to Archive')

# ── Convert active 3. All-Purpose Card notes ─────────────────────────────────
# Skip any that were just archived
archived_cids = {cid for cid, _ in all_archive}

cur.execute(f"""SELECT DISTINCT n.id, n.flds, c.id FROM notes n
    JOIN cards c ON c.nid = n.id
    WHERE c.did IN ({ph}) AND n.mid = ?
    AND c.queue != -1""", list(JAPANESE_DECK_IDS) + [ALL_PURPOSE_ID])

rows = cur.fetchall()
# Deduplicate by note id, skip archived cards
seen_nids = set()
to_convert = []
for nid, flds, cid in rows:
    if cid not in archived_cids and nid not in seen_nids:
        seen_nids.add(nid)
        to_convert.append((nid, flds))

print(f'\nNotes to convert: {len(to_convert)}')

# Old field order: [0]Prompt [1]Picture [2]Context [3]Answer [4]FullSolution [5]ExtraInfo [6]TestSpelling
# New field order: [0]Prompt [1]Context [2]Image-Front [3]Answer [4]Furigana [5]Full-Solution [6]Image-Back [7]Audio
converted = 0
for nid, flds in to_convert:
    old = flds.split(SEP)
    # Pad to 7 fields in case some are missing
    while len(old) < 7:
        old.append('')

    prompt       = old[0].strip()
    picture      = old[1].strip()
    context      = old[2].strip()
    answer       = old[3].strip()
    full_sol     = old[4].strip()
    extra        = old[5].strip()
    # old[6] test spelling — dropped

    new_fields = [prompt, context, picture, answer, extra, full_sol, '', '']
    new_flds = SEP.join(new_fields)

    cur.execute("UPDATE notes SET flds = ?, sfld = ?, mid = ?, mod = ? WHERE id = ?",
                (new_flds, prompt, TARGET_NOTETYPE_ID, int(time.time()), nid))
    converted += 1

print(f'  Converted {converted} notes to Japanese Fill-in-the-Blank')

conn.commit()
conn.close()
print(f'\nDone. Open Anki — changes will be picked up automatically.')
print(f'Backup at: {BACKUP_PATH}')
