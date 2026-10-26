"""Phase 12 skeptic: independent recomputation of the three primary B2-vs-B0 holdout results.
REPRODUCTION-class arithmetic on the committed predictions and the already-opened sealed labels;
it does not select among candidates. No memelab import."""
import csv, gzip, json, sys, math, datetime as dt
import numpy as np
root = sys.argv[1]  # audits/predictive-intelligence
H = dt.datetime(2026,10,17,tzinfo=dt.timezone.utc).timestamp()
E = dt.datetime(2026,10,24,tzinfo=dt.timezone.utc).timestamp()
TG = {"price_path_target_before_invalidation_24h":"T1_24h","price_path_target_before_invalidation_6h":"T1b_6h","price_path_severe_drawdown_or_halt_24h":"T2_24h"}
CONTACTED = {("CnPL1xnAVHYGH92FpmiNoNhgh3gctkH5y988hMg4bonk", "2026-10-17T10:20:42Z"),("Tm2iqbxYjKpW8xCMe6q1xUraNMNzcG5xMztAir3pump","2026-10-19T10:34:05Z")}
def iso(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
rows = [json.loads(l) for l in gzip.open(f"{root}/phase_06/sealed/holdout_labels.jsonl.gz","rt")]
print("sealed rows", len(rows), "decision time range", iso(min(r["decision_time"] for r in rows)), iso(max(r["decision_time"] for r in rows)))
print("rows at/after 2026-10-24:", sum(r["decision_time"]>=E for r in rows))
dec = {r["decision_key"]: r for r in csv.DictReader(open(f"{root}/phase_12/validation/HOLDOUT_DECISIONS.csv"))}
pred = {}
for r in csv.DictReader(open(f"{root}/phase_12/validation/HOLDOUT_PREDICTIONS.csv")):
    if r["number"] != "": pred[(r["target_short"], r["decision_key"], r["candidate"])] = float(r["number"])
excl = {}
data = {}
for r in rows:
    t = TG[r["target"]]
    contacted = (r["mint"], iso(r["decision_time"])) in CONTACTED
    if contacted != bool(r["holdout_contacted"]): print("FLAG DISAGREES", r["mint"])
    ok = (H <= r["decision_time"] < E and r["split"]=="HOLDOUT" and r["state"]=="LABELED" and r["censored"]==0 and r["label"] in (0,1)
          and r["target_version"]=="1" and r["labels_version"]=="labels-1" and r["label_observed_at"]>=r["label_matures_at"]
          and r["chain"]=="solana" and r["decision_key"] in dec and dec[r["decision_key"]]["mint"]==r["mint"])
    if ok and contacted: excl[t]=excl.get(t,0)+1; continue
    if not ok: continue
    b2 = pred.get((t, r["decision_key"], "P07_B2")); b0 = pred.get((t, r["decision_key"], "P07_B0"))
    if b2 is None or b0 is None: continue
    day = iso(r["decision_time"])[:10]
    data.setdefault(t, []).append((r["label"], b2, b0, day, r["mint"]))
def boot(y,p,q,groups,reps=20000,seed=12345):
    rng=np.random.default_rng(seed); g=np.array(groups); u=np.unique(g); idx=[np.where(g==k)[0] for k in u]
    out=np.empty(reps)
    for i in range(reps):
        s=np.concatenate([idx[j] for j in rng.integers(0,len(u),len(u))])
        bs=np.mean((p[s]-y[s])**2); b0=np.mean((q[s]-y[s])**2)
        out[i]=1-bs/b0 if b0>0 else np.nan
    return out
def wilson(k,n,z=1.959963984540054):
    ph=k/n; d=1+z*z/n; c=(ph+z*z/(2*n))/d; h=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/d; return c-h,c+h
res={}
for t in ["T1_24h","T1b_6h","T2_24h"]:
    a=data[t]; y=np.array([x[0] for x in a],float); p=np.array([x[1] for x in a]); q=np.array([x[2] for x in a])
    bs=np.mean((p-y)**2); b0=np.mean((q-y)**2); bss=1-bs/b0
    days=[x[3] for x in a]; mints=[x[4] for x in a]
    bd=boot(y,p,q,days); bm=boot(y,p,q,mints)
    di=np.nanpercentile(bd,[2.5,97.5]); mi=np.nanpercentile(bm,[2.5,97.5])
    gov = "day" if (di[1]-di[0])>=(mi[1]-mi[0]) else "mint"
    g = bd if gov=="day" else bm
    pval=(1+np.sum(g<=0))/(len(g)+1)
    ll=lambda pp: -np.mean(y*np.log(np.clip(pp,1e-6,1-1e-6))+(1-y)*np.log(np.clip(1-pp,1e-6,1-1e-6)))
    res[t]=dict(n=len(y),pos=int(y.sum()),days=len(set(days)),mints=len(set(mints)),prev=y.mean(),wilson=wilson(int(y.sum()),len(y)),b0_value=float(q[0]),
                brier_b2=bs,brier_b0=b0,bss=bss,day_ci=list(di),mint_ci=list(mi),gov=gov,p=pval,ll_b2=ll(p),ll_b0=ll(q),mean_pred=p.mean(),excluded_contacted=excl.get(t,0))
ps=sorted(res, key=lambda t: res[t]["p"]); m=len(ps); run=0
for i,t in enumerate(ps):
    run=max(run,min(1,(m-i)*res[t]["p"])); res[t]["holm"]=run
for t,v in res.items():
    print(t, json.dumps({k:(round(x,4) if isinstance(x,float) else ([round(z,4) for z in x] if isinstance(x,(list,tuple)) else x)) for k,x in v.items()}))
# NC1: share of the 20 shuffled-training seeds whose holdout BSS is above the real B2's, on the same scored rows
print("NC1 check")
for t in ["T1_24h","T1b_6h","T2_24h"]:
    a=data[t]; keys=[]
    for r in rows:
        pass
    y=np.array([x[0] for x in a],float); q=np.array([x[2] for x in a]); real=res[t]["bss"]
    dk=[r["decision_key"] for r in rows if TG[r["target"]]==t]
    # rebuild decision keys in the same order as data[t]
    order=[]
    for r in rows:
        tt=TG[r["target"]]
        if tt!=t: continue
        b2=pred.get((t,r["decision_key"],"P07_B2"))
        if b2 is None: continue
        if (r["mint"], iso(r["decision_time"])) in CONTACTED: continue
        if not (r["state"]=="LABELED" and r["censored"]==0 and r["label"] in (0,1) and r["label_observed_at"]>=r["label_matures_at"] and r["decision_key"] in dec): continue
        order.append(r["decision_key"])
    assert len(order)==len(a)
    bss=[]
    for s in range(20):
        p=np.array([pred.get((t,k,f"NC1_seed{s:02d}"),np.nan) for k in order]); m=np.isfinite(p)
        bss.append(1-np.mean((p[m]-y[m])**2)/np.mean((q[m]-y[m])**2))
    print(t, "mean NC1 BSS", round(float(np.mean(bss)),4), "share above real", np.mean(np.array(bss)>real))
