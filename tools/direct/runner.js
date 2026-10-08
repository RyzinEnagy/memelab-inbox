// usage: node runner.js <plan.json> <out.json>  -- runs collector.js in Node with stubbed window/document
const fs=require('fs'),vm=require('vm');
const doc={body:{innerHTML:''},getElementById:()=>({textContent:''}),documentElement:{}};
const ctx={window:{},document:doc,fetch,performance,console,setTimeout,URL,JSON,Promise,Date,Math,DOMParser:undefined,location:{},history:{}};
ctx.window=ctx; vm.createContext(ctx);
for(const f of ['collector','chains','catalyst']){try{vm.runInContext(fs.readFileSync(process.env.MLJS+'/'+f+'.js','utf8'),ctx,{filename:f})}catch(e){console.error('load',f,e.message)}}
(async()=>{const plan=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
 console.log(await ctx.__ML.run(plan,6)); fs.writeFileSync(process.argv[3],ctx.__ML.last);})();
