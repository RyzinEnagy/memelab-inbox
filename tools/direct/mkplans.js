// usage: MLJS=<dir with collector/chains/catalyst.js> node mkplans.js <in.json> <cfgs.json> <syms.json> <date> <out.json>
const fs=require('fs'),vm=require('vm');
const ctx={document:{body:{},getElementById:()=>({}),documentElement:{}},fetch,performance,console,setTimeout,URL,JSON,Promise,Date,Math};ctx.window=ctx;vm.createContext(ctx);
for(const f of ['collector','chains','catalyst'])vm.runInContext(fs.readFileSync(process.env.MLJS+'/'+f+'.js','utf8'),ctx);
const [inp,cfgs,sym]=[2,3,4].map(i=>JSON.parse(fs.readFileSync(process.argv[i])));const D=process.argv[5];const plans=[];
for(const t of inp.tokens.solana||[]){const p=ctx.__ML.deepPlan(`wl_${sym[t[0]]}_${D}`,[t],inp.native.solana);
 p.reqs.push({key:`jup_tok:${t[0]}`,url:`https://lite-api.jup.ag/tokens/v2/search?query=${t[0]}`},{key:`rug:${t[0]}`,url:`https://api.rugcheck.xyz/v1/tokens/${t[0]}/report`,delayMs:250},{key:`ds:batch:0`,url:`https://api.dexscreener.com/tokens/v1/solana/${t[0]}`});
 plans.push({chain:'solana',addr:t[0],plan:p});}
for(const ch of Object.keys(inp.tokens)){if(ch==='solana')continue;for(const t of inp.tokens[ch]){
 // EVM addresses MUST be lowercase: the bundle builder looks pools/tokens up by lowercase key
 const tt=[t[0].toLowerCase(),t[1].toLowerCase(),t[2],t[3],t[4]];
 const p=ctx.__ML.evmDeepPlan(`wl_${sym[t[0]]||sym[tt[0]]}_${D}`,ch,cfgs[ch],[tt],inp.native[ch]);
 p.reqs.push({key:`ds:${ch}:one:${tt[0]}`,url:`https://api.dexscreener.com/tokens/v1/${ch}/${tt[0]}`,proj:'ds'});
 plans.push({chain:ch,addr:tt[0],plan:p});}}
fs.writeFileSync(process.argv[6],JSON.stringify(plans));console.log(plans.map(p=>p.plan.id+' '+p.plan.reqs.length).join('\n'));
