"""Isolated micro-probes of literal code-path behaviors from baseline 698f73b.
Not an import of the repository and NOT an end-to-end acceptance test.
No external network, secrets, production database, or accounts used.
"""
from __future__ import annotations
import json, re, sqlite3, tempfile
from pathlib import Path

results = []

def probe(name, actual, expected=True):
    ok = actual == expected
    results.append((name, 'PASS' if ok else 'FAIL', str(actual)))
    assert ok, (name, actual, expected)

# memelab/secrets.py: literal _KEY_IN_URL regex and redact expression
rx = re.compile(r'(api-key=)[^&"\'\s\\]+')
redacted = rx.sub(r'\1REDACTED', 'https://helius.test/?api-key=FAKE-KEY Authorization: Bearer FAKE-BEARER')
probe('Helius URL api-key is masked', 'api-key=REDACTED' in redacted)
probe('Generic bearer text survives redact', 'Bearer FAKE-BEARER' in redacted)

# memelab/social/llm.py: load_config only checks top-level keys
forbidden = {'api_key','key','token','secret','anthropic_api_key','authorization','password'}
raw = {'provider':'anthropic', 'model':'fixture', 'notes':{'api_key':'INVENTED-DO-NOT-USE'}}
bad = sorted(k for k in raw if k.lower() in forbidden)
probe('Nested key passes top-level LLM config check', bad == [])

# memelab/social/private.py: get() does not test retain_until
with tempfile.TemporaryDirectory() as d:
    dbp = Path(d) / 'private.sqlite'
    con = sqlite3.connect(dbp)
    con.execute('CREATE TABLE private_content(private_ref TEXT PRIMARY KEY, exact_text TEXT, retain_until REAL)')
    con.execute('INSERT INTO private_content VALUES(?,?,?)',('sha256:test','invented expired content',1.0))
    con.commit()
    fetched = con.execute('SELECT * FROM private_content WHERE private_ref=?',('sha256:test',)).fetchone()
    probe('Expired private text still returned until purge', fetched is not None)
    con.close()

# memelab/social/alerts_transport.py: success handling requires dict shape.
for attack in (['unexpected', 'array'], 'unexpected-scalar'):
    try:
        _ = attack.get('ok')   # mirrors send() success branch, outside its try/except
        escaped = False
    except AttributeError:
        escaped = True
    probe(f'Unexpected Telegram response shape raises {type(attack).__name__}', escaped)

# memelab/social/llm.py: provider text concatenation assumes str chunks.
try:
    _ = ''.join(block.get('text', '') for block in [{'type':'text','text':42}] if block.get('type')=='text')
    escaped = False
except TypeError:
    escaped = True
probe('Malformed LLM text chunk raises TypeError', escaped)

# memelab/social/llm.py: monthly allow() counts rows but does not reserve quota.
with tempfile.TemporaryDirectory() as d:
    file = Path(d)/'spend.sqlite'
    c1=sqlite3.connect(file)
    c1.execute('CREATE TABLE social_api_spend(connector TEXT, mode TEXT, billing_day TEXT, est_cost_usd REAL)')
    c1.commit()
    c2=sqlite3.connect(file)
    def used(c):
        return c.execute("SELECT COUNT(*) FROM social_api_spend WHERE mode='live' AND connector='llm:anthropic' AND substr(billing_day,1,7)='2026-10'").fetchone()[0]
    allowed_one = used(c1) < 1
    allowed_two = used(c2) < 1
    c1.execute('INSERT INTO social_api_spend VALUES(?,?,?,?)',('llm:anthropic','live','2026-10-13',0.1));c1.commit()
    c2.execute('INSERT INTO social_api_spend VALUES(?,?,?,?)',('llm:anthropic','live','2026-10-13',0.1));c2.commit()
    probe('Interleaved quota checks admit 2 calls against limit 1', allowed_one and allowed_two and used(c1)==2)
    c1.close();c2.close()

# memelab/social/private.py: mkdir(..., exist_ok=True), sqlite3.connect(path)
# without explicit mode hardening. Demonstrates runtime default on this POSIX host.
import os, stat
with tempfile.TemporaryDirectory() as d:
    parent = Path(d) / 'private'
    old_umask = os.umask(0o022)
    try:
        parent.mkdir(parents=True, exist_ok=True)
        fp = parent / 'social_private.sqlite'
        c = sqlite3.connect(fp)
        c.execute('CREATE TABLE demo(txt TEXT)')
        c.close()
        probe('Default private directory mode under umask 022 is 0755', stat.S_IMODE(parent.stat().st_mode) == 0o755)
        probe('Default SQLite database mode under umask 022 is 0644', stat.S_IMODE(fp.stat().st_mode) == 0o644)
    finally:
        os.umask(old_umask)

for name,status,details in results:
    print(f'{status:4} | {name} | {details}')
print(f'\n{sum(s=="PASS" for _,s,_ in results)}/{len(results)} isolated micro-probes passed')
