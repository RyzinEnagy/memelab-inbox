# Signing the private predictive state (ED-9, PI-D-132)

No key was created. Without a key everything works as before and the state reads as UNSIGNED_NO_KEY.

## What is signed

After each pass the engine writes `STATE_SIGNATURE.json` next to `PASSES.jsonl` with HMAC-SHA256 over
`memelab-predictive-state-sig-1|<seq>|<tip record id>`. The tip pass record commits to the previous pass and to the sha256 of
every state file, so one signature covers the whole state. With a key configured, `load_state` refuses (STATE_TAMPERED) a
state with passes and no signature, a signature naming another pass, or a signature that does not match. This closes the
reseal attack of F20-08: rewriting a line and recomputing every record id and file sha256 is caught once a key is set.

## Where the key lives

The key is a file named `predictive_state.key` in the memelab folder on the computer the scheduled tasks use, next to
`gh_token.txt` and `firecrawl_token.txt`: `C:\Users\<you>\memelab\predictive_state.key`, which a scheduled session sees as
`~/mnt/memelab/predictive_state.key` (the connected folder). It must be outside the git checkout the engine runs from: the
scheduled sessions rebuild the project from `main` in their own folder, so the connected folder is outside it. If the memelab
folder on the computer is itself a git checkout, the engine refuses the file there; keep it one folder up instead. The name is
in `.gitignore` as a second guard.

1. Create it once (64 hex characters, 256 bits):
   `python -c "import secrets; print(secrets.token_hex(32))" > predictive_state.key`
   run inside that memelab folder (on macOS or Linux also `chmod 600 predictive_state.key`).
2. Point the engine at it in the environment of every process that runs the scout or the reports:
   `MEMELAB_PREDICTIVE_STATE_KEY_FILE=$HOME/mnt/memelab/predictive_state.key` in a scheduled session (the exact line is in
   `FLAG_ON.md`). The alternative `MEMELAB_PREDICTIVE_STATE_KEY` (the value itself) works but puts the key in the process
   environment; the file is preferred.
3. The key only means something when the state persists between sessions, so the scheduled run also points `state_dir` at the
   connected folder (`FLAG_ON.md`). Adopt the existing state once: run `python -m memelab.predictive.integration check` (must report no problem), then
   `python -m memelab.predictive.integration sign`. Check with `sign-status` (SIGNED_VERIFIED).

Rules the code enforces: a key file inside the repository is refused; a key under 32 bytes is refused; the key is never printed
and never appears in a message. Keep a copy of the key file somewhere safe: without it a signed state cannot be verified, and
`sign` with a new key re-signs only a state whose chain still checks.

## Statuses (`sign-status`)

| Status | Meaning |
|---|---|
| UNSIGNED_NO_KEY | no key configured, no signature file (allowed) |
| SIGNATURE_NOT_VERIFIED_NO_KEY | a signature file exists but no key is configured, so it was not checked |
| EMPTY_STATE | no pass yet |
| SIGNED_VERIFIED | key configured, chain and signature check |
| REFUSED | key configured and the state or the key is refused (reason given, never the key) |
