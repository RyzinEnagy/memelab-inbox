// memelab social bridge helpers: shape inbound social observations for the inbox route.
// Load after collector.js in the tab that will ship the result:  eval(<this file>)
// The public inbox never carries post text (DECISIONS D-010, D-013): hash it here, keep only the hash,
// numeric metrics and an own-words summary. The ingester quarantines items that carry text, bios, media,
// DMs, member lists or anything not PUBLIC. Contract: memelab/social/ingest.py (INBOUND_SCHEMA).
(() => {
  const ML = window.__ML || (window.__ML = {});
  const SCHEMA = "memelab.social.inbound/1";
  // same normalization as memelab.social.store.normalize_text: NFC, whitespace runs -> one space, trimmed
  const norm = (t) => String(t).normalize("NFC").replace(/\s+/g, " ").trim();
  async function hash(text) {
    const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(norm(text)));
    return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
  }
  // source: {platform, source_id, access_mode, collector, rights_basis, visibility:"PUBLIC", terms_note?, url?}
  // items: [{provider_item_id|url, account:{handle|provider_user_id, profile_url?}, published_at?, content_hash?, summary?, metrics?}]
  // challenge: "login" | "captcha" | "blocked" when the page asked for one (stop, record, never solve).
  function put(source, items, opts = {}) {
    const key = `soc:${source.platform}:${source.source_id}`;
    const out = ML.last ? JSON.parse(ML.last) : { _plan: opts.plan || `soc_${Date.now()}`, _at: new Date().toISOString(), _n: 0 };
    const body = { schema: SCHEMA, source, fetched_at: opts.fetched_at || new Date().toISOString(), items: items || [] };
    out[key] = opts.challenge ? { s: 0, err: `challenge: ${opts.challenge}`, challenge: opts.challenge, body: null }
                              : { s: opts.status || 200, len: JSON.stringify(body).length, ms: 0, body, err: opts.err || null };
    out._n = Object.keys(out).filter((k) => !k.startsWith("_")).length;
    ML.last = JSON.stringify(out);
    return `${key}: ${opts.challenge ? "challenge " + opts.challenge : (items || []).length + " items"}`;
  }
  window.__SOC = { SCHEMA, norm, hash, put };
  return "social.js loaded";
})();
