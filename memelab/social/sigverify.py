"""Phase 09: verify a signed message against a public wallet address. Pure Python, no new dependency, no private key anywhere.

A signature proves that whoever holds the key signed those exact bytes. It says nothing about who that person is, and a copied signature
proves nothing about the person who posted it, so the caller also checks that the message names the account (see wallet_assertions.bound).

  Solana   ed25519 over the raw message bytes (what wallet 'signMessage' produces). Address = base58 public key.
  EVM      EIP-191 personal_sign: keccak256("\\x19Ethereum Signed Message:\\n" + len + message), secp256k1 recovery, address compare.
  other    UNSUPPORTED (never guessed).

verify() returns (status, detail) with status in VALID, INVALID, UNSUPPORTED, MALFORMED.
"""
from __future__ import annotations

import base64
import binascii
import hashlib

from ..chains import registry as chain_registry
from ._keccak import eip55, keccak256

VERSION = "sigverify-v1"
_ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58decode(s: str) -> bytes:
    n = 0
    for ch in s:
        i = _ALPH.find(ch)
        if i < 0:
            raise ValueError("not base58")
        n = n * 58 + i
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\x00" * (len(s) - len(s.lstrip("1"))) + raw


def b58encode(b: bytes) -> str:
    n, out = int.from_bytes(b, "big"), ""
    while n:
        n, r = divmod(n, 58)
        out = _ALPH[r] + out
    return "1" * (len(b) - len(b.lstrip(b"\x00"))) + out


def decode_signature(s: str, length: int) -> bytes:
    """Accept hex (with or without 0x), base58 or base64, whichever gives exactly `length` bytes."""
    s = s.strip()
    cands = []
    h = s[2:] if s.lower().startswith("0x") else s
    try:
        cands.append(binascii.unhexlify(h))
    except (binascii.Error, ValueError):
        pass
    try:
        cands.append(b58decode(s))
    except ValueError:
        pass
    try:
        cands.append(base64.b64decode(s, validate=True))
    except (binascii.Error, ValueError):
        pass
    for c in cands:
        if len(c) == length:
            return c
    raise ValueError(f"signature is not {length} bytes in hex, base58 or base64")


# ---------- ed25519 (RFC 8032 verification) ----------
_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _recover_x(y: int, sign: int) -> int | None:
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * _I % _P
    if (x * x - x2) % _P != 0:
        return None
    return _P - x if (x & 1) != sign else x


_GY = 4 * pow(5, _P - 2, _P) % _P
_G = (_recover_x(_GY, 0), _GY, 1, 0)
_G = (_G[0], _G[1], 1, _G[0] * _G[1] % _P)


def _add(p, q):
    a = (p[1] - p[0]) * (q[1] - q[0]) % _P
    b = (p[1] + p[0]) * (q[1] + q[0]) % _P
    c = 2 * p[3] * q[3] * _D % _P
    d = 2 * p[2] * q[2] % _P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _mul(s: int, p):
    q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _add(q, p)
        p = _add(p, p)
        s >>= 1
    return q


def _eq(p, q) -> bool:
    return (p[0] * q[2] - q[0] * p[2]) % _P == 0 and (p[1] * q[2] - q[1] * p[2]) % _P == 0


def _decompress(b: bytes):
    y = int.from_bytes(b, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


def ed25519_verify(public: bytes, message: bytes, signature: bytes) -> bool:
    if len(public) != 32 or len(signature) != 64:
        return False
    a, r = _decompress(public), _decompress(signature[:32])
    if a is None or r is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:
        return False
    h = int.from_bytes(hashlib.sha512(signature[:32] + public + message).digest(), "little") % _L
    return _eq(_mul(s, _G), _add(r, _mul(h, a)))


# ---------- secp256k1 recovery (EIP-191) ----------
_SP = 2 ** 256 - 2 ** 32 - 977
_SN = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_SG = (0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
       0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def _sadd(p, q):
    if p is None:
        return q
    if q is None:
        return p
    if p[0] == q[0]:
        if (p[1] + q[1]) % _SP == 0:
            return None
        lam = 3 * p[0] * p[0] * pow(2 * p[1], _SP - 2, _SP) % _SP
    else:
        lam = (q[1] - p[1]) * pow(q[0] - p[0], _SP - 2, _SP) % _SP
    x = (lam * lam - p[0] - q[0]) % _SP
    return (x, (lam * (p[0] - x) - p[1]) % _SP)


def _smul(k: int, p):
    out = None
    while k:
        if k & 1:
            out = _sadd(out, p)
        p = _sadd(p, p)
        k >>= 1
    return out


def eth_recover(digest: bytes, r: int, s: int, rec_id: int) -> bytes | None:
    if not (1 <= r < _SN and 1 <= s < _SN) or rec_id not in (0, 1):
        return None
    x = r
    y2 = (pow(x, 3, _SP) + 7) % _SP
    y = pow(y2, (_SP + 1) // 4, _SP)
    if y * y % _SP != y2:
        return None
    if (y & 1) != rec_id:
        y = _SP - y
    z = int.from_bytes(digest, "big")
    rinv = pow(r, _SN - 2, _SN)
    q = _sadd(_smul(s * rinv % _SN, (x, y)), _smul((-z * rinv) % _SN, _SG))
    if q is None:
        return None
    return q[0].to_bytes(32, "big") + q[1].to_bytes(32, "big")


def eip191_digest(message: bytes) -> bytes:
    return keccak256(b"\x19Ethereum Signed Message:\n" + str(len(message)).encode() + message)


def verify(chain: str, address: str, message: bytes, signature: str) -> tuple[str, str]:
    try:
        fam = chain_registry.family(chain)
    except Exception:
        return "UNSUPPORTED", f"unknown chain {chain!r}"
    if not message:
        return "MALFORMED", "empty message"
    if fam == "solana":
        try:
            pub = b58decode(address)
            sig = decode_signature(signature, 64)
        except ValueError as e:
            return "MALFORMED", str(e)
        if len(pub) != 32:
            return "MALFORMED", "address is not a 32 byte public key"
        return ("VALID", "ed25519 signature matches the address") if ed25519_verify(pub, message, sig) else ("INVALID", "ed25519 signature does not match")
    if fam == "evm":
        try:
            sig = decode_signature(signature, 65)
        except ValueError as e:
            return "MALFORMED", str(e)
        v = sig[64]
        rec = v - 27 if v in (27, 28) else v if v in (0, 1) else None
        if rec is None:
            return "MALFORMED", "recovery byte must be 27, 28, 0 or 1"
        pub = eth_recover(eip191_digest(message), int.from_bytes(sig[:32], "big"), int.from_bytes(sig[32:64], "big"), rec)
        if pub is None:
            return "INVALID", "no public key recovers from this signature"
        got = "0x" + keccak256(pub)[12:].hex()
        want = address.strip().lower()
        if got == want:
            return "VALID", f"recovered signer {eip55(got)} matches the address"
        return "INVALID", f"recovered signer {got[:10]}... is a different address"
    return "UNSUPPORTED", f"signature checks are not built for {fam} chains"
