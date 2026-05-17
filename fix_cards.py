"""
One-shot script to fix Anki card hints and remove ChatGPT picture placeholder text.
Run with Anki CLOSED.
"""
import sqlite3, shutil, os, sys
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.expandvars(r'%APPDATA%\Anki2\Teraku\collection.anki2')
BACKUP_PATH = DB_PATH + f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

shutil.copy2(DB_PATH, BACKUP_PATH)
print(f'Backup: {BACKUP_PATH}')

conn = sqlite3.connect(DB_PATH)
conn.create_collation('unicase', lambda a, b: (a.lower() > b.lower()) - (a.lower() < b.lower()))
cur = conn.cursor()

FIELD_SEP = '\x1f'

def get_fields(nid):
    cur.execute('SELECT flds FROM notes WHERE id = ?', (nid,))
    return cur.fetchone()[0].split(FIELD_SEP)

def set_context(nid, new_context):
    fields = get_fields(nid)
    old = fields[1]
    fields[1] = new_context
    cur.execute('UPDATE notes SET flds = ?, mod = ? WHERE id = ?',
                (FIELD_SEP.join(fields), int(datetime.now().timestamp()), nid))
    print(f'  NID {nid}: context updated')
    print(f'    old: {old}')
    print(f'    new: {new_context}')

# ── Hint fixes ────────────────────────────────────────────────────────────────

print('\n── Hint fixes ──')

# 1. 部長はただいま外出______ (NID 1774601361399)
# Wrong label: 尊敬語 — actually 謙譲語 + ております
set_context(1774601361399,
    'Business keigo set phrase: reporting a superior\'s absence to a visitor/caller — which ending?')

# 2. この店はあの店______安くありません (NID 1774599810647)
# ほど comparative — hint is fine, no change needed beyond clarity
set_context(1774599810647,
    'Comparative pattern: A is not as ~ as B | particle expressing "to the extent/degree of B"')

# 3. 日本食は見た目も大切______言われています (NID 1774795256651)
# Too leading: names both という and passive
set_context(1774795256651,
    'Copula + quotation particle before 言われています — what links 大切 (na-adj) to 言われて?')

# 4. 毎日お菓子を食べ______、太りますよ (NID 1774601338073)
# Wrong verb group (食べる is Group 1 / ichidan) + hint names すぎる directly
set_context(1774601338073,
    'Group 1 verb: 食べる | Eating sweets every day to excess — what attaches to the verb stem before the consequence?')

# 5. ご不明な点がございましたら、何でもお申し______ください (NID 1774601361400)
# Fixed keigo phrase — hint should cue the verb, not just say "set expression"
set_context(1774601361400,
    'Fixed keigo phrase using 付ける | お申し＿＿ください — what is the 連用形 of 付ける?')

# ── Remove ChatGPT picture placeholder from Image-Front (field index 2) ───────

print('\n── ChatGPT picture placeholder cleanup ──')

JAPANESE_DECK_IDS = (1738918480114, 1738918480115, 1716403620198,
                     1738918480116, 1773012065806, 1769985523000)
placeholders = ','.join('?' * len(JAPANESE_DECK_IDS))

cur.execute(f'''
    SELECT DISTINCT n.id, n.flds FROM notes n
    JOIN cards c ON c.nid = n.id
    WHERE c.did IN ({placeholders})
    AND n.flds LIKE '%FIND A MATCHING PICTURE%'
''', JAPANESE_DECK_IDS)

rows = cur.fetchall()
print(f'  Found {len(rows)} cards to clean')
for nid, flds in rows:
    fields = flds.split(FIELD_SEP)
    # Field 2 is Image-Front
    old_val = fields[2]
    # Strip the placeholder — keep any surrounding whitespace clean
    import re
    fields[2] = re.sub(r'FIND A MATCHING PICTURE FOR ME, PLEASE\.?', '', fields[2]).strip()
    if not fields[2]:
        fields[2] = '　'  # keep the field non-empty with a fullwidth space like other empty fields
    cur.execute('UPDATE notes SET flds = ?, mod = ? WHERE id = ?',
                (FIELD_SEP.join(fields), int(datetime.now().timestamp()), nid))
    print(f'  NID {nid}: image-front cleaned')
    print(f'    old: {repr(old_val[:80])}')
    print(f'    new: {repr(fields[2][:80])}')

# ── ばかり vs しか contrastive context ──────────────────────────────────────────

print('\n── ばかり vs しか context unification ──')

BAKARI_SHIKA_CONTEXT = 'ばかり vs しか | ばかり＝肯定形（〜ばかり買っています）/ しか＝否定形（〜しか買えません） | exclusive focus: nothing but ~'

BAKARI_SHIKA_NIDS = [
    1774599810665,  # 最近はこのブランド______買っています (ばかり)
    1774599855324,  # Sサイズ______残っていないんですか (しか)
    1774599855328,  # セール品______見て、結局何も買わなかった (ばかり)
    1774599810660,  # この商品______買えません (しか)
    1774599810666,  # 値段のことばかり______、デザインを忘れていた (ばかり)
    1774599855327,  # 最近はネットショッピング______しています (ばかり)
    1774599855323,  # このお店には現金______使えません (しか)
    1774599810661,  # 今日は千円______持っていません (しか)
    1774599810662,  # このサイズ______残っていません (しか)
]

for nid in BAKARI_SHIKA_NIDS:
    set_context(nid, BAKARI_SHIKA_CONTEXT)

# ── New てしまう cards ──────────────────────────────────────────────────────────

print('\n── New てしまう cards ──')

import time, json

CLAUDE_DECK_ID = 1773012065806
NOTETYPE_ID = 1769985345426
FIELD_SEP = '\x1f'

def insert_card(prompt, context, answer, furigana, full_solution):
    now_ms = int(time.time() * 1000)
    # Ensure unique IDs by spacing them out
    nid = now_ms
    time.sleep(0.002)
    cid = int(time.time() * 1000)

    flds = FIELD_SEP.join([prompt, context, '　', answer, furigana, full_solution, '', ''])
    cur.execute('''INSERT INTO notes (id, guid, mid, mod, usn, tags, flds, sfld, csum, flags, data)
        VALUES (?, ?, ?, ?, -1, '', ?, ?, 0, 0, '')''',
        (nid, str(nid), NOTETYPE_ID, int(time.time()), flds, prompt))

    cur.execute('''INSERT INTO cards (id, nid, did, ord, mod, usn, type, queue, due, ivl, factor, reps, lapses, left, odue, odid, flags, data)
        VALUES (?, ?, ?, 0, ?, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, '{}')''',
        (cid, nid, CLAUDE_DECK_ID, int(time.time())))

    print(f'  Inserted note {nid} / card {cid}: {prompt[:60]}')

# Card 1: forgetting something carelessly (caregiver of error)
insert_card(
    prompt='遅刻しそうだったのに、取りに戻らなければならなかった。財布を家に______。',
    context='unintended action with regretful consequence — て-form compound | Group 1 verb: 忘れる',
    answer='忘れてしまった',
    furigana='忘[わす]れてしまった',
    full_solution='遅刻しそうだったのに、取りに戻らなければならなかった。財布を家に忘れてしまった。'
)

# Card 2: irreversible completion (something broken/gone)
insert_card(
    prompt='昨日買ったばかりなのに、もう______。',
    context='irreversible completion with regret — て-form compound | Group 2 verb: 壊れる',
    answer='壊れてしまった',
    furigana='壊[こわ]れてしまった',
    full_solution='昨日買ったばかりなのに、もう壊れてしまった。'
)

# Card 3: unintended negative consequence of own action (active/transitive)
insert_card(
    prompt='ウォーミングアップをサボったせいで、______。',
    context='unintended negative consequence of one\'s own action — て-form compound | verb: 怪我をする',
    answer='怪我をしてしまった',
    furigana='怪我[けが]をしてしまった',
    full_solution='ウォーミングアップをサボったせいで、怪我をしてしまった。'
)

conn.commit()
conn.close()
print('\nDone. Open Anki — changes will be picked up automatically.')
print(f'Backup at: {BACKUP_PATH}')
