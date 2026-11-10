# Signing the private predictive state (ED-9, PI-D-132)

No key was created. Without a key everything works as before and the state reads as UNSIGNED_NO_KEY.

## What is signed

After each pass the engine writes `STATE_SIGNATURE.json` next to `PASSES.jsonl` with HMAC-SHA256 over
`memelab-predictive-state-sig-1|<seq>|<tip record id>`. The tip pass record commits to the previous pass and to the sha256 of
every state file, so one signature covers the whole state. With a key configured, `load_state` refuses (STATE_TAMPERED) a
state with passes and no signature, a signature naming another pass, or a signature that does not match. This closes the
reseal attack of F20-08: rewriting a line and recomputing every record id and file sha256 is caught once a key is set.

## Rollback (PI-D-139, after the skeptic's m1)

The signature binds the last seq and tip, so on its own it cannot tell a current state from an older signed copy of the same
folder. After every signature the engine therefore also writes the last signed seq and tip, with their own HMAC, to a counter
file outside the state folder, keyed by the resolved state folder path:

- `MEMELAB_PREDICTIVE_STATE_SEQ_FILE` when set; else
- next to the key file: `predictive_state.key.last_seq.json`; else (key given by value)
- next to the state folder: `<state folder>.last_seq.json`.

A counter file inside the state folder is refused. With a key, `load_state` (and so every pass, report and `sign-status`)
refuses a state whose last seq is below the counter, a state with the counter's seq and another tip, a counter entry the key did
not write, and an unreadable counter file. `sign` never adopts a chain below the counter. Restoring an older copy on purpose
means removing that folder's entry from the counter file by hand, then `check` and `sign`.

## Where the key lives (PI-D-138, PI-D-139, after the skeptic's m2)

The key gets a folder of its own, separate from the state folder: `%USERPROFILE%\memelab-key\predictive_state.key` on the
computer the scheduled tasks use, connected to each memelab scheduled task as a second folder, which the session sees as
`~/mnt/memelab-key/predictive_state.key`. The engine looks there by itself (`integration.DEFAULT_KEY_FILE`) when neither
environment variable is set, so the scheduled prompt never names the key (PI-D-138). It must be outside any git checkout: the
engine refuses a key file inside the repository, and the name is in `.gitignore` as a second guard. The rollback counter is
written beside it.

1. Create it once (64 hex characters, 256 bits), in the new `memelab-key` folder:
   `python -c "import secrets; print(secrets.token_hex(32))" > predictive_state.key`
   (on macOS or Linux also `chmod 600 predictive_state.key`).
2. Connect `%USERPROFILE%\memelab-key\` to each memelab scheduled task as a folder. On a computer that runs the engine by
   hand, `MEMELAB_PREDICTIVE_STATE_KEY_FILE` names the file instead; `MEMELAB_PREDICTIVE_STATE_KEY` (the value itself) works
   but puts the key in the process environment.
3. The key only means something when the state persists between sessions, so the scheduled run also points `state_dir` at the
   connected memelab folder (`FLAG_ON.md`). Adopt an existing state once, by hand: `python -m memelab.predictive.integration
   check` (must report no problem), then `python -m memelab.predictive.integration sign`. Check with `sign-status`
   (SIGNED_VERIFIED).

What a separate key folder protects, said plainly:

- It protects against stray or partial edits of the state, a copy, sync or restore of the state folder alone (including an
  older copy, through the counter), and any person, tool or session that has the state folder but not the key folder.
- It does not protect against the scheduled session itself, or anything else that can read the key folder: whoever holds the
  key can rewrite the state, re-sign it and update the counter. The signature proves that the state was last written by a
  holder of the key, not that the holder behaved. A key the scheduled session cannot read would need a signing step outside
  the session, which is not part of CM-3.

Rules the code enforces: a key file inside the repository is refused; a key under 32 bytes is refused; the key is never printed
and never appears in a message; a signature or counter HMAC that is not 64 lower-case hex characters (non-ASCII included) is
StateTampered, never a TypeError (skeptic m4). Keep a copy of the key file somewhere safe: without it a signed state cannot be
verified, and `sign` with a new key re-signs only a state whose chain still checks.

## Statuses (`sign-status`)

| Status | Meaning |
|---|---|
| UNSIGNED_NO_KEY | no key configured, no signature file (allowed) |
| SIGNATURE_NOT_VERIFIED_NO_KEY | a signature file exists but no key is configured, so it was not checked |
| EMPTY_STATE | no pass yet |
| SIGNED_VERIFIED | key configured, chain and signature check |
| REFUSED | key configured and the state, the key or the rollback counter is refused (reason given, never the key) |
