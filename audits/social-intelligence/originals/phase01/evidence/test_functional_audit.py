"""Independent Phase 01 acceptance probes. Synthetic only; no production edits."""
import copy,json,sqlite3,sys
from pathlib import Path
import pytest
from memelab import db
from memelab.social import ingest as I,store,schema,identity,extraction as E,narratives as N,feed_store as FS,feed_core as FC
from memelab.social import registry_import as RI,registry as R,wallet_assertions as W,wallet_activity as WA
from memelab.social import alpha_core as AC,research_core as RC,research_store as RS
from memelab.social import alerts_engine as AE,alerts_core as AL,outcomes_core as OC,outcomes_ledger as OL,x_api as X
from memelab.modules import m24_opportunity_ranker as Rank
ROOT=Path.cwd(); FX=ROOT/'tests/fixtures/social'
RES=json.loads((FX/'resolve/fx_providers.json').read_text()); CA=RES['addresses']['M1']
T=1791763200.; H=3600.; NOW=T+20*H

@pytest.fixture
def env(tmp_path,monkeypatch):
 monkeypatch.setenv('MEMELAB_PRIVATE_DB',str(tmp_path/'private.sqlite'))
 monkeypatch.setenv('MEMELAB_LLM_CONFIG',str(tmp_path/'no-model.json'))
 p=tmp_path/'main.sqlite'; db.init_db(p)
 c=sqlite3.connect(p); c.row_factory=sqlite3.Row
 yield p,c,tmp_path
 c.close()

class Adapter:
 name='audit'
 def __init__(self,units): self.batches=units
 def units(self,budget): yield from self.batches

def unit(pid,author,text,ref=None,connector='audit:x'):
 post={'id':pid,'author_id':author,'created_at':'2026-10-12T01:00:00Z','text':text}
 if ref: post['referenced_tweets']=[{'type':'retweeted','id':ref}]
 it=X.post_item(post,{author:{'id':author,'username':'audit_'+author}}, {},T+H+60,True)
 body={'schema':I.INBOUND_SCHEMA_V2,'source':{'platform':'x','access_mode':'fixture','collector':'audit','rights_basis':'synthetic_fixture'},'fetched_at':T+H+60,'items':[it]}
 return I.SourceUnit(connector,'x',pid,'OK',I.canonical_sha(body),body)

def collect(env):
 p,c,_=env
 texts=['Watching Solana '+CA,'Researching liquidity for '+CA,'Watching Solana '+CA]
 units=[unit('1001','2001',texts[0]),unit('1002','2002',texts[1]),unit('1003','2003',texts[2],'1001')]
 out=I.ingest(Adapter(units),p,now=T+2*H,qdir=False)
 assert out['counts']['created']==3
 return units,texts

def count(c,table): return c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]

def bridge_extract(env):
 units,texts=collect(env); p,c,_=env
 for i,text in enumerate(texts):
  oid=c.execute('SELECT id FROM social_observations WHERE item_key=?',('x:'+str(1001+i),)).fetchone()[0]
  result=E.extract_observation(c,oid,text,bodies=RES['bodies'],now=T+2*H)
  assert result['deterministic']['status']=='ok'
 c.commit()
 return units,texts

def snap(c,now=NOW): return N.snapshot(c,window_start=T,window_end=T+86400,now=now,params={'require_coverage':False})

def test_A_primary_ingestion_reaches_claims_without_manual_handoff(env):
 collect(env); _,c,_=env
 assert count(c,'social_observations')==3
 assert count(c,'social_claims')>0, 'ACTUAL: three observations, zero automatic claims (AUD-003)'

def test_A_explicit_handoff_resolves_groups_cites_and_repeats(env):
 units,texts=bridge_extract(env);p,c,_=env
 r=snap(c); c.commit()
 cl=next(x for x in r['clusters'] if x['cluster_key']=='ca:solana:'+CA)
 assert cl['item_count']==3 and cl['independent_source_count']==2 and cl['amplifier_count']==1
 inp=FS.load_input(c,as_of=NOW,include_fixtures=True)
 doc=FC.build(inp); md=FC.render(doc,'brief')
 assert CA in md
 assert all('https://x.com/audit_'+str(2001+i)+'/status/'+str(1001+i) in md for i in range(3))
 before=count(c,'social_claims'); I.ingest(Adapter(units),p,now=NOW+60,qdir=False)
 for i,text in enumerate(texts):
  oid=c.execute('SELECT id FROM social_observations WHERE item_key=?',('x:'+str(1001+i),)).fetchone()[0]
  E.extract_observation(c,oid,text,bodies=RES['bodies'],now=T+2*H)
 assert count(c,'social_observations')==3 and count(c,'social_claims')==before
 assert FC.to_json(FC.build(inp))==FC.to_json(doc)
 print('A: three observations, exact Solana identity, two independent sources, one repost; citations and fixed-input feed deterministic')

def test_token_ticker_collision_abstains():
 res=identity.resolve_post(RES['bodies'],text='$PEPE',chain_hint='solana')
 assert res['mentions'] and all(x['status']!='resolved' for x in res['mentions'])

def test_extraction_wrong_text_fails_closed(env):
 collect(env);_,c,_=env
 oid=c.execute('SELECT id FROM social_observations LIMIT 1').fetchone()[0]
 r=E.extract_observation(c,oid,'Unrelated fabricated claim',now=NOW)
 assert r['deterministic']['reason']=='text_hash_mismatch' and count(c,'social_claims')==0

def test_source_registration_discovery_idempotent(env):
 _,c,_=env
 f=FX/'registry/leaderboard_fresh.json'
 RI.import_file(c,f,now=NOW); n=count(c,'social_registry_entities'); assert n>0
 RI.import_file(c,f,now=NOW); assert count(c,'social_registry_entities')==n
 rows=[dict(r) for r in c.execute('SELECT * FROM social_registry_entities')]
 assert all(x['is_fixture'] for x in rows)
 print('Imported candidate entities:',n,'; no automatic human identity proof')

def test_B_400_percent_premention_move_not_credited():
 import importlib.util
 s=importlib.util.spec_from_file_location('audit_alpha_builder',FX/'alpha/make_alpha.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 call=m.call('audit-late','audit-trader','LATE',12)
 series=m.series('LATE',[(0,1),(11,5),(m.HOURS,5)])
 controls=[m.series('CONTROL'+str(i),[(0,1),(m.HOURS,1)]) for i in range(6)]
 doc={'schema':AC.SCHEMA,'is_fixture':True,'label':'FIXTURE audit','as_of':m.T0+m.HOURS*m.H,'calls':[call],'series':[series]+controls,'sources':{}}
 r=AC.analyze(doc,{'horizons_s':[86400],'primary_horizon_s':86400}); x=r['calls'][0]
 assert x['entry']['price']==5
 assert x['horizons']['86400']['net']<=0 and x['horizons']['86400']['relative']==0
 print('B: premention +400%; entry 5; postmention relative return 0, not +400%')

def test_C_core_risk_checks_survive_social_enrichment():
 raw=Rank.evaluate(holders={'largest_unexplained_pct':30,'adjusted_top10_pct':85},depth={'exit_capacity_usd_5pct':100,'sell_impact_5k_pct':60})
 flags={x['flag'] for x in raw['fatal_flags']}
 assert {'LARGEST_HOLDER_GT_15PCT','TOP10_GT_50PCT','CANNOT_EXIT_5K'}<=flags
 fx=json.loads((FX/'research/scout_before_after.json').read_text()); f=copy.deepcopy(fx['findings'][0]);f.update(independent_source_count=100,confidence='HIGH')
 ev=[{'chain':f['chain'],'contract':f['contract'],'status':raw['status'],'score':raw['total'],'fatal_flags':list(flags),'untradeable':True,'in_tradable_ranking':False,'workflow':'scout'}]
 out=RC.build([f],ev,RC.make_policy({'include_fixtures':True}),as_of=fx['as_of']); c=out['candidates'][0]
 assert c['research_state']=='REJECTED_STRUCTURE' and not c['in_tradable_ranking']
 print('C: raw module fatal flags',sorted(flags),'; social attention cannot clear rejection')

def test_D_unavailable_unit_preserves_pages_other_connector_retry(env):
 p,c,_=env; a=unit('1010','2010','First '+CA); b=unit('1011','2011','Other '+CA,connector='audit:other')
 down=I.SourceUnit('audit:x','x','page2','DOWN','d'*64,error='synthetic outage')
 r=I.ingest(Adapter([a,down,b]),p,now=NOW,qdir=False)
 assert r['status']=='PARTIAL' and r['health']['audit:x']['status']=='DOWN' and r['health']['audit:other']['status'] in ('OK','DEGRADED')
 assert count(c,'social_observations')==2
 I.ingest(Adapter([a,b]),p,now=NOW+60,qdir=False); assert count(c,'social_observations')==2
 assert c.execute("SELECT COUNT(*) FROM social_coverage WHERE status='GAP'").fetchone()[0]==1
 print('D normalized-unavailable path: survives, gap stored, other connector OK, duplicate-free retry')

def test_D_adapter_iterator_exception_is_contained(env):
 p,c,_=env
 class Crash:
  name='crash'
  def units(self,budget):
   yield unit('1020','2020','Partial '+CA)
   raise TimeoutError('synthetic API outage while fetching next page')
 try: r=I.ingest(Crash(),p,now=NOW,qdir=False)
 except TimeoutError:
  status=c.execute('SELECT status FROM social_ingest_runs ORDER BY started_at DESC LIMIT 1').fetchone()[0]
  assert False, 'ACTUAL: exception escapes; persisted observation count='+str(count(c,'social_observations'))+'; run remains '+status+'; no final DOWN health'
 assert r['status']=='PARTIAL'

def test_empty_and_missing_credentials(env):
 p,c,_=env
 assert I.ingest(Adapter([]),p,now=NOW,qdir=False)['counts']['created']==0
 doc=FC.build(FS.load_input(c,as_of=NOW)); assert doc['items']==[] and doc['headline']==FC.NO_SIGNAL
 h=X.health(FX/'x_api/fx_x_config.json',p,env={},now=NOW)
 print('Missing credentials health:',h)
 assert 'MISSING' in json.dumps(h).upper() or 'NOT_CONFIGURED' in json.dumps(h).upper()

def test_schema_migration_preserves_legacy_rows_and_reopen(env):
 _,_,tmp=env; p=tmp/'legacy-copy.sqlite'
 src=sqlite3.connect(ROOT/'data/memelab.sqlite'); dst=sqlite3.connect(p);src.backup(dst);src.close()
 tables=[r[0] for r in dst.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
 before={t:dst.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in tables}
 schema.migrate(dst); assert schema.current_version(dst)==12
 assert schema.migrate(dst)==[]
 assert {t:dst.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in tables}==before
 dst.commit();dst.close();dst=sqlite3.connect(p);assert schema.current_version(dst)==12;dst.close()
 print('Migration: copied public database, all',len(tables),'legacy table counts preserved, version 12 after reopen')

def test_historical_late_extraction_excluded(env):
 bridge_extract(env);_,c,_=env
 c.execute('UPDATE social_claim_extractions SET extracted_at=?',(NOW+86400,))
 r=snap(c)
 assert not r['clusters'], 'ACTUAL: later extractions populate past snapshot (AUD-001)'

def test_historical_explicit_future_run_rejected(env):
 bridge_extract(env);_,c,_=env
 r=snap(c,now=NOW+86400);c.commit()
 inp=FS.load_input(c,as_of=NOW,include_fixtures=True,run_id=r['run_id'])
 assert not inp['clusters'], 'ACTUAL: explicit run_id bypasses cutoff; future snapshot is returned'

def test_wallet_activity_idempotence_no_identity_upgrade(env):
 _,c,_=env
 ix=json.loads((FX/'wallets/index.json').read_text()); wallet=ix['wallets']['T1'];t=ix['now']
 WA.add_wallet(c,'solana',wallet,reason='audit fixture',added_by='auditor',fixture=True,now=ix['t0'])
 WA.ingest_file(c,FX/'wallets/fx_helius_ok.json',now=t,fixture=True);n=count(c,'social_wallet_events');assert n>0
 WA.ingest_file(c,FX/'wallets/fx_helius_ok.json',now=t,fixture=True);assert count(c,'social_wallet_events')==n
 assert WA.list_wallets(c)[0]['owner_claimed'] is None
 print('Wallet classified events:',n,'; duplicate-free; owner remains unknown')

def test_wallet_disclosure_is_not_control_proof(env):
 _,c,_=env
 entity=R.ensure_account(c,'x',handle='audit_wallet',provider_user_id='9901',now=NOW)
 wallet=json.loads((FX/'wallets/index.json').read_text())['wallets']['T1']
 W.record(c,account_entity=entity,chain='solana',wallet_address=wallet,evidence_type='OFFICIAL_SELF_DISCLOSURE',evidence_ref='https://example.invalid/wallet',recorded_by='auditor',now=NOW)
 v=W.explain(c,entity,'solana',wallet,as_of=NOW,now=NOW)
 assert v['level']!='VERIFIED_CONTROL'
 assert all(x['counts_as']!='CONTROL_PROOF' for x in v['assertions'])
 print('Self disclosure level:',v['level'])

def test_alert_repeat_dry_run_no_remote_delivery(env):
 _,_,tmp=env
 sys.path.insert(0,str(ROOT/'tests'));import test_social_alerts as helper
 con=AE.connect(tmp/'alerts.sqlite');feed=helper.feed([helper.item()]);pol=AL.make_policy({})
 r=AE.run(con,feed=feed,policy=pol,mode='dry_run',now=helper.T0,transports=[])
 n=con.execute('SELECT COUNT(*) FROM alert_events').fetchone()[0];assert n>0
 AE.run(con,feed=feed,policy=pol,mode='dry_run',now=helper.T0+60,transports=[])
 assert con.execute('SELECT COUNT(*) FROM alert_events').fetchone()[0]==n
 assert con.execute("SELECT COUNT(*) FROM alert_deliveries WHERE status='DELIVERED'").fetchone()[0]==0
 con.close()

def test_outcome_ledger_append_idempotence_and_integrity(env):
 _,_,tmp=env;sys.path.insert(0,str(ROOT/'tests'));import test_social_outcomes as helper
 p=tmp/'signals.sqlite';con=OL.connect(p);pol=OC.make_policy({})
 sig=helper.sig();OL.record_signals(con,[sig],pol,now=helper.G+10,is_fixture=True);n=len(OL.dump(con))
 OL.record_signals(con,[sig],pol,now=helper.G+10,is_fixture=True);assert len(OL.dump(con))==n
 OL.add_observations(con,helper.series(helper.E,helper.E+2*H,300,lambda t:1.0),pol,now=helper.E+3*H)
 OL.evaluate_all(con,as_of=helper.E+3*H,pol=pol,now=helper.E+3*H)
 assert OL.latest_outcomes(con); assert OL.verify(con)['ok']
 n=len(OL.dump(con));con.close();con=OL.connect(p);assert len(OL.dump(con))==n and OL.verify(con)['ok'];con.close()

def test_model_output_cannot_invent_a_resolved_token(env):
 from memelab.social import llm
 units,texts=collect(env);_,c,_=env
 sys.path.insert(0,str(ROOT/'tests'));import test_social_extraction as helper
 text=texts[0];oid=c.execute("SELECT id FROM social_observations WHERE item_key='x:1001'").fetchone()[0]
 raw=helper.resp(helper.claim(tokens=[{'mention_id':'nonexistent'}]))
 provider=llm.MockProvider({store.text_hash(text):[raw]})
 r=E.extract_observation(c,oid,text,bodies=RES['bodies'],provider=provider,now=T+2*H)
 claims=E.claims_for(c,item_key='x:1001')
 assert not any(x['extractor']=='model' and x['tokens'] for x in claims)
 assert provider.calls
 print('Mock invented-token output status:',r['model']['status'],'; no fabricated resolved token persisted')

def test_wallet_performance_recomputes_and_abstains_on_incomplete_history():
 from memelab.social import perf_analysis as PA
 doc=json.loads((FX/'perf/ledger_main.json').read_text());r=PA.analyze(doc)
 assert PA.analyze(copy.deepcopy(doc))['result_sha256']==r['result_sha256']
 assert not r['score']['rankable']
 print('Wallet performance score gate:',r['score'])

def test_historical_feed_ignores_chronology_created_after_cutoff(env):
 from memelab.social import chrono_core as CC,chrono_store as CS
 _,c,_=env
 doc=json.loads((FX/'chrono/confident.json').read_text());r=CC.analyze(doc)
 assert r['flags']
 CS.save_run(c,doc,r,now=doc['as_of']+86400);c.commit()
 tok=r['token'];flags=FS._flags(c,tok['chain'],tok['contract'],doc['as_of'],True)
 assert not flags, 'ACTUAL: '+str(len(flags))+' chronology flags created a day later appear in historical feed'

def test_D_partial_collection_report_discloses_gap(env):
 bridge_extract(env);p,c,_=env
 down=I.SourceUnit('audit:x','x','outage','DOWN','e'*64,error='synthetic outage')
 I.ingest(Adapter([down]),p,now=T+3*H,qdir=False)
 snap(c);c.commit()
 doc=FC.build(FS.load_input(c,as_of=NOW,include_fixtures=True));md=FC.render(doc,'brief')
 assert doc['items'] and all(x['freshness']['coverage']['counts_are_lower_bounds'] for x in doc['items'])
 assert 'lower bounds' in md and 'GAP' in md
 print('D report: GAP disclosed; counts lower bounds; no complete-coverage claim')

def test_chronology_saved_run_recomputes_idempotently(env):
 from memelab.social import chrono_core as CC,chrono_store as CS
 _,c,_=env;doc=json.loads((FX/'chrono/confident.json').read_text());r=CC.analyze(doc)
 s=CS.save_run(c,doc,r,now=doc['as_of']);n=count(c,'social_chrono_runs')
 again=CS.save_run(c,doc,r,now=doc['as_of']);assert not again['created'] and count(c,'social_chrono_runs')==n
 assert CS.verify_run(c,s['run_id'])['verified']
