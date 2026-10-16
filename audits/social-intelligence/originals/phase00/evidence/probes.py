import json,sqlite3,tempfile,runpy,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();sys.path.insert(0,str(root))
from memelab import db
from memelab.social import schema,store,replay_sources as RS,narratives as NR,llm
out={}
with tempfile.TemporaryDirectory() as td:
 p=Path(td)/'lab.sqlite';db.init_db(p)
 x=runpy.run_path(str(root/'tests/test_social_x_api.py'))
 f=x['fixture'](x['ALPHA_USER'],x['ex']('/2/users/2000000000000000001/tweets',x['BASE'],body={'data':[x['post'](5,text='Invented fixture '+ '8CyKBGPYjSHmrGsiJg8W5uN9BSzS3gA3E7YLGmQ3tgkJ')],'meta':{'next_token':'page2'}}))
 r,_,_=x['run'](p,f,config=x['cfg'](max_pages_per_scope=1,**x['ONLY_USER']))
 c=sqlite3.connect(p);c.row_factory=sqlite3.Row
 out['x_ingest']={'created':r['counts']['created'],'claims':c.execute('SELECT COUNT(*) FROM social_claims').fetchone()[0],'resolutions':c.execute('SELECT COUNT(*) FROM social_token_resolutions').fetchone()[0],'cursor':dict(c.execute('SELECT newest_id,last_status FROM social_source_cursors WHERE connector=?',(x['USER'],)).fetchone()),'health':r['health'][x['USER']]['status']}
 c.close()
 q=Path(td)/'replay.sqlite';c=sqlite3.connect(q);c.row_factory=sqlite3.Row;schema.migrate(c)
 c.execute("INSERT INTO social_analysis_versions(version,component,created_at) VALUES ('v1','extractor',100)")
 c.execute("INSERT INTO social_accounts(account_id,platform,first_seen_at,last_seen_at) VALUES ('x:id:1','x',100,100)")
 c.execute("INSERT INTO social_token_refs(ref_key,ref_kind,chain,contract,first_seen_at) VALUES ('ca:solana:a','CONTRACT_ADDRESS','solana','a',100)")
 c.execute("INSERT INTO social_items(item_key,platform,account_id,published_at,first_observed_at,first_ingested_at) VALUES ('x:1','x','x:id:1',100,120,130)")
 c.execute("INSERT INTO social_claims(claim_key,item_key,account_id,claim_type,token_ref_id,direction,claimed_at,extracted_at,analysis_version) VALUES ('cl1','x:1','x:id:1','CALL',1,'LONG',100,10000,'v1')")
 c.commit();c.close();doc=RS.from_db(str(q));out['replay_availability']={'extracted_at':10000,'exported_available_at':doc['posts'][0]['available_at']}
 # Is the narrative cutoff applied to extraction time?
 n=runpy.run_path(str(root/'tests/test_social_narratives.py'));z=Path(td)/'narr.sqlite';db.init_db(z);c=sqlite3.connect(z);c.row_factory=sqlite3.Row
 store.register_analysis_version(c,n['EXTRACT_V'],'extractor','audit builder',now=n['D1'])
 n['cover'](c);n['post'](c,'audit_late','audit_source',n['D1']+3600,tokens=[n['tok']('solana',n['M1'])]);late=n['D2']+86400
 c.execute('UPDATE social_claim_extractions SET extracted_at=?',(late,));c.execute('UPDATE social_claims SET extracted_at=?',(late,))
 snap=NR.snapshot(c,day='2026-10-12',now=n['D2']);out['narrative_availability']={'cutoff':n['D2'],'extracted_at':late,'clusters':len(snap['clusters'])}
 from memelab.social import alpha_store
 ai=alpha_store.build_input(c,as_of=n['D2'])
 out['alpha_fixture_label']={'input_is_fixture':ai['is_fixture'],'calls':len(ai['calls']),'observation_access_mode':c.execute('SELECT access_mode FROM social_observations').fetchone()[0]}
 c.close()
 # No paid call: budget arithmetic only.
 c=sqlite3.connect(':memory:');schema.migrate(c)
 b=llm.Budget(max_usd_per_month=0,price_in=0,price_out=0)
 out['zero_price_budget']={'cap':0,'input_price':0,'output_price':0,'allow_reason':b.allow(c,'llm:a','live',1000,1791849600)}
 c.close()
print(json.dumps(out,indent=2,sort_keys=True))
