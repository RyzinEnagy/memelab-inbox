// Run fetch plans and the in-browser JS steps directly from the sandbox (or any machine with Node 18+). No browser needed.
// Loads the same collector + projections the browser uses, so result files are identical to shipped ones.
//
//   node run_plan.js <plan.json> <out.result.json> [--conc N]            run a saved plan
//   node run_plan.js - <out.result.json> --pre <prev.result.json> --js "<code>"
//        preload a previous result (what the browser tab would have rendered), then evaluate <code> with __ML available.
//        If the code returns a plan ({id, reqs}), that plan is run; otherwise whatever the code rendered is written.
//        Examples: --js 'await __ML.screen({minLiq:20000,minVol:50000})'
//                  --js 'await __ML.stage2(["mint1","mint2"], {keep: 8})'
//                  --js '__ML.deepPlan("deep_x", [[mint, pool, 6, price, liq]], 150)'
const fs = require("fs"), path = require("path"), vm = require("vm");
const argv = process.argv.slice(2);
const opt = (name) => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : undefined; };
const [planPath, outPath] = argv;
if (!planPath || !outPath) { console.error("usage: node run_plan.js <plan.json|-> <out.result.json> [--conc N] [--pre file] [--js code]"); process.exit(2); }
const conc = Number(opt("--conc")) || 6;
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36";
const nodeFetch = globalThis.fetch;
globalThis.fetch = (url, init = {}) => nodeFetch(url, { ...init, headers: { "User-Agent": UA, Accept: "application/json, text/plain, */*", ...(init.headers || {}) }, signal: AbortSignal.timeout(45000) });
const el = { textContent: "" };
globalThis.window = globalThis;
globalThis.document = { body: { set innerHTML(v) {}, get innerText() { return el.textContent; } }, documentElement: {}, getElementById: () => el, querySelector: () => null };
globalThis.location = { href: "node:run_plan" };
for (const f of ["collector.js", "chains.js", "launch.js", "catalyst.js", "screen.js", "stage2.js"]) {
  const p = path.join(__dirname, f);
  if (fs.existsSync(p)) vm.runInThisContext(fs.readFileSync(p, "utf8"), { filename: p });
}

async function runWithRetries(plan) {
  let summary = await window.__ML.run(plan, conc);
  // rate-limited or dropped requests get two slower retry rounds; results merge into the same output
  for (let round = 1; round <= 2; round++) {
    const keep = JSON.parse(window.__ML.last);
    const again = plan.reqs.filter(r => !keep[r.key] || keep[r.key].s === 429 || keep[r.key].s === 0);
    if (!again.length) break;
    process.stderr.write(`\nretry round ${round}: ${again.length} request(s) after ${20 * round}s\n`);
    await new Promise(r => setTimeout(r, 20000 * round));
    await window.__ML.run({ id: plan.id, reqs: again }, 1);
    const fresh = JSON.parse(window.__ML.last);
    for (const r of again) keep[r.key] = fresh[r.key];
    window.__ML.last = JSON.stringify(keep); el.textContent = window.__ML.last;
    summary = `${plan.reqs.filter(r => keep[r.key] && keep[r.key].s === 200).length}/${plan.reqs.length} ok after retries`;
  }
  const out = JSON.parse(window.__ML.last);
  const failed = plan.reqs.filter(r => !out[r.key] || out[r.key].s !== 200).map(r => `${r.key} (${out[r.key] ? out[r.key].s + " " + (out[r.key].err || "") : "missing"})`);
  return { summary, failed };
}

(async () => {
  const t0 = Date.now();
  const timer = setInterval(() => { try { process.stderr.write(`\r${window.__ML.progress()}  `); } catch {} }, 5000);
  let res = null, text;
  const pre = opt("--pre");
  if (pre) { window.__ML.last = fs.readFileSync(pre, "utf8"); el.textContent = window.__ML.last; }
  const code = opt("--js");
  if (planPath !== "-") {
    res = await runWithRetries(JSON.parse(fs.readFileSync(planPath, "utf8")));
    text = window.__ML.last;
  }
  if (code) {
    const ret = await vm.runInThisContext(`(async () => (${code}))()`);
    if (ret && Array.isArray(ret.reqs)) { res = await runWithRetries(ret); text = window.__ML.last; }
    else { text = el.textContent || window.__ML.last; res = { summary: typeof ret === "string" ? ret : JSON.stringify(ret).slice(0, 300), failed: [] }; }
  }
  clearInterval(timer);
  fs.writeFileSync(outPath, text);
  console.log(`\n${res.summary} in ${Math.round((Date.now() - t0) / 1000)}s -> ${outPath}`);
  if (res.failed.length) console.log("FAILED (use the Chrome bridge for these only if they matter):\n  " + res.failed.join("\n  "));
})().catch(e => { console.error(e); process.exit(1); });
