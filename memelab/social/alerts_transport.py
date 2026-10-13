"""Phase 15: where alerts go.

  FileSink           the operational sink: one text file per alert in a local outbox folder (gitignored by default,
                     data/private/alerts_outbox/). Writing it is a local file, never a message to a device, and every
                     output says so.
  TelegramTransport  one authorized bot posting plain text to one chat. The bot token is read only from the
                     environment (MEMELAB_ALERT_TELEGRAM_TOKEN), the chat id from the environment or the private config.
  EmailTransport     SMTP with STARTTLS. Host, port, user, sender and recipient from the private config or environment;
                     the password only from the environment (MEMELAB_ALERT_SMTP_PASSWORD).

Remote transports exist only when their credentials are configured and the private config opts in. A private config
that contains a secret is refused (the repo is public; secrets live in the environment). Errors are redacted before
they are stored or printed. Network access goes through an injectable `http` or `smtp` callable so tests never reach
the network.

Private config: data/private/alerts.json (override MEMELAB_ALERT_CONFIG). Example in docs/social-intelligence/alerts.example.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

CONFIG_SCHEMA = "memelab.social.alerts.config/1"
TELEGRAM_TOKEN_ENV = "MEMELAB_ALERT_TELEGRAM_TOKEN"
TELEGRAM_CHAT_ENV = "MEMELAB_ALERT_TELEGRAM_CHAT_ID"
SMTP_PASSWORD_ENV = "MEMELAB_ALERT_SMTP_PASSWORD"
SECRET_KEYS = re.compile(r"(token|password|secret|api[_-]?key|bearer)", re.I)
_TG_TOKEN = re.compile(r"\b\d{6,12}:[A-Za-z0-9_\-]{30,}\b")
_BOT_PATH = re.compile(r"/bot[^/\s]+/")

DEFAULT_CONFIG: dict[str, Any] = {
    "schema": CONFIG_SCHEMA,
    "notifications_opt_in": False,   # the owner's consent to receive messages at all
    "send_enabled": False,           # a second switch: even with --send nothing leaves the machine without it
    "outbox": None,                  # default data/private/alerts_outbox
    "policy": {},                    # overrides merged over alerts_core.DEFAULT_POLICY
    "telegram": {"enabled": False, "chat_id": None},
    "email": {"enabled": False, "host": None, "port": 587, "user": None, "sender": None, "to": None},
}


class ConfigError(ValueError):
    pass


def redact(s: Any) -> str:
    from . import ingest
    t = ingest.redact(str(s))
    t = _TG_TOKEN.sub("[REDACTED]", t)
    t = _BOT_PATH.sub("/bot[REDACTED]/", t)
    for env in (TELEGRAM_TOKEN_ENV, SMTP_PASSWORD_ENV):
        v = os.environ.get(env)
        if v and len(v) >= 4:
            t = t.replace(v, "[REDACTED]")
    return t[:300]


def dest_ref(transport: str, dest: str | None) -> str | None:
    """A stable reference to a destination that does not reveal it (stored in the ledger)."""
    return None if not dest else hashlib.sha256(f"{transport}:{dest}".encode()).hexdigest()[:12]


def _scan_secrets(v: Any, path: str = "") -> list[str]:
    hits = []
    if isinstance(v, dict):
        for k, x in v.items():
            if SECRET_KEYS.search(str(k)) and x not in (None, "", False):
                hits.append(f"{path}{k}")
            hits += _scan_secrets(x, f"{path}{k}.")
    elif isinstance(v, str) and _TG_TOKEN.search(v):
        hits.append(path.rstrip(".") or "value")
    return hits


def default_config_path() -> Path:
    env = os.environ.get("MEMELAB_ALERT_CONFIG")
    if env:
        return Path(env)
    from .. import db
    return Path(db.DB_PATH).parent / "private" / "alerts.json"


def load_config(path: str | Path | None = None) -> dict:
    """Missing file: defaults (dry-run only). A file holding a secret is refused, naming the key, never the value."""
    p = Path(path) if path else default_config_path()
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if p.exists():
        try:
            raw = json.loads(p.read_text())
        except ValueError as e:
            raise ConfigError(f"{p.name} is not valid JSON") from e
        hits = _scan_secrets(raw)
        if hits:
            raise ConfigError(f"{p.name} holds a secret at {', '.join(sorted(hits))}; secrets come from the environment only "
                              f"({TELEGRAM_TOKEN_ENV}, {SMTP_PASSWORD_ENV})")
        if raw.get("schema", CONFIG_SCHEMA) != CONFIG_SCHEMA:
            raise ConfigError(f"config schema must be {CONFIG_SCHEMA}")
        for k, v in raw.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict) and k != "policy":
                cfg[k].update(v)
            else:
                cfg[k] = v
        cfg["_path"] = str(p)
    else:
        cfg["_path"] = None
    return cfg


@dataclass
class Result:
    ok: bool
    retryable: bool = False
    error: str | None = None
    retry_after: float | None = None


class FileSink:
    name = "file"
    remote = False

    def __init__(self, outbox: str | Path):
        self.outbox = Path(outbox)

    def destination(self) -> str:
        return str(self.outbox)

    def send(self, alert_id: int, text: str, *, preview: bool) -> Result:
        try:
            d = self.outbox / ("preview" if preview else "sent")
            d.mkdir(parents=True, exist_ok=True)
            (d / f"alert_{alert_id:06d}.txt").write_text(text)
            return Result(True)
        except OSError as e:
            return Result(False, retryable=True, error=redact(f"{type(e).__name__}: {e}"))


def _urllib_post(url: str, body: dict, timeout: float = 15.0) -> tuple[int, dict]:
    import urllib.error
    import urllib.request
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310  fixed https host
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except ValueError:
            return e.code, {}


class TelegramTransport:
    name = "telegram"
    remote = True

    def __init__(self, token: str, chat_id: str, http: Callable[[str, dict], tuple[int, dict]] | None = None):
        self._token = token
        self.chat_id = str(chat_id)
        self._http = http or _urllib_post

    def destination(self) -> str:
        return self.chat_id

    def send(self, alert_id: int, text: str, *, preview: bool) -> Result:
        if preview:
            return Result(False, error="dry run: not sent")
        try:
            status, body = self._http(f"https://api.telegram.org/bot{self._token}/sendMessage",
                                      {"chat_id": self.chat_id, "text": text[:4000], "disable_web_page_preview": True})
        except Exception as e:  # noqa: BLE001  network errors are retryable; the message never says sent
            return Result(False, retryable=True, error=redact(f"{type(e).__name__}: {e}"))
        if status == 200 and body.get("ok") is True:
            return Result(True)
        desc = redact(body.get("description") or f"HTTP {status}")
        if status == 429:
            ra = (body.get("parameters") or {}).get("retry_after")
            return Result(False, retryable=True, error=f"HTTP 429 {desc}", retry_after=float(ra) if ra else None)
        return Result(False, retryable=status >= 500, error=f"HTTP {status} {desc}")


class EmailTransport:
    name = "email"
    remote = True

    def __init__(self, *, host: str, port: int, user: str | None, password: str | None, sender: str, to: str,
                 smtp: Callable[..., Any] | None = None):
        self.host, self.port, self.user, self._password, self.sender, self.to = host, int(port), user, password, sender, to
        self._smtp = smtp

    def destination(self) -> str:
        return self.to

    def send(self, alert_id: int, text: str, *, preview: bool) -> Result:
        if preview:
            return Result(False, error="dry run: not sent")
        from email.message import EmailMessage
        msg = EmailMessage()
        msg["Subject"] = text.splitlines()[0][:120] if text else "memelab research alert"
        msg["From"], msg["To"] = self.sender, self.to
        msg.set_content(text)
        try:
            if self._smtp:
                self._smtp(msg)
            else:
                import smtplib
                with smtplib.SMTP(self.host, self.port, timeout=20) as s:
                    s.starttls()
                    if self.user:
                        s.login(self.user, self._password or "")
                    s.send_message(msg)
            return Result(True)
        except Exception as e:  # noqa: BLE001
            import smtplib
            permanent = isinstance(e, (smtplib.SMTPAuthenticationError, smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused))
            return Result(False, retryable=not permanent, error=redact(f"{type(e).__name__}: {e}"))


def build_transports(cfg: dict, *, outbox: str | Path, http=None, smtp=None, env: dict | None = None) -> tuple[list, list[dict]]:
    """The file sink always; a remote transport only when the config enables it and its credentials exist.
    Returns (transports, notes) where notes say why a remote transport is absent (never the secret)."""
    env = os.environ if env is None else env
    out, notes = [FileSink(outbox)], []
    tg = cfg.get("telegram") or {}
    if tg.get("enabled"):
        token = (env.get(TELEGRAM_TOKEN_ENV) or "").strip()
        chat = (env.get(TELEGRAM_CHAT_ENV) or str(tg.get("chat_id") or "")).strip()
        if not token or not chat:
            notes.append({"transport": "telegram", "status": "not_configured",
                          "detail": "missing " + " and ".join(x for x, ok in ((TELEGRAM_TOKEN_ENV, token), ("chat id", chat)) if not ok)})
        else:
            out.append(TelegramTransport(token, chat, http=http))
    else:
        notes.append({"transport": "telegram", "status": "disabled", "detail": "not enabled in the private config"})
    em = cfg.get("email") or {}
    if em.get("enabled"):
        need = {k: em.get(k) for k in ("host", "sender", "to")}
        missing = [k for k, v in need.items() if not v]
        pw = env.get(SMTP_PASSWORD_ENV)
        if em.get("user") and not pw:
            missing.append(SMTP_PASSWORD_ENV)
        if missing:
            notes.append({"transport": "email", "status": "not_configured", "detail": "missing " + ", ".join(missing)})
        else:
            out.append(EmailTransport(host=em["host"], port=em.get("port") or 587, user=em.get("user"), password=pw,
                                      sender=em["sender"], to=em["to"], smtp=smtp))
    else:
        notes.append({"transport": "email", "status": "disabled", "detail": "not enabled in the private config"})
    return out, notes
