"""Run new probes in an already clean disposable pinned checkout, with no credentials."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

PIN='698f73b854567ce60b56ce275b5ab6822a9d5f60'


def main():
    p=argparse.ArgumentParser();p.add_argument('--checkout',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    here=Path(__file__).resolve().parent;root=a.checkout.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==PIN
    assert subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True)==''
    before=hashlib.sha256((root/'data/memelab.sqlite').read_bytes()).hexdigest()
    guard=here.parent/'independent_m00/network_guard';network=out/'network-events.log';network.write_text('')
    raw=Path(tempfile.mkdtemp(prefix='phase03-replication-raw-'))
    records=[]
    with tempfile.TemporaryDirectory(prefix='phase03-replication-env-') as tmp:
        env={'PATH':str(Path(sys.executable).parent)+':/usr/bin:/bin','HOME':tmp,'TMPDIR':tmp,'PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONPATH':str(guard)+os.pathsep+str(root),'M00_NETWORK_LOG':str(network),'MEMELAB_PRIVATE_DB':tmp+'/private.sqlite','MEMELAB_LLM_CONFIG':tmp+'/none.json'}
        for name,args,expected in [('characterization',[str(here/'probe_cases.py'),'--out',str(out/'observations.json')],0),('safety-acceptance',['-m','pytest',str(here/'test_safety_acceptance.py'),'-q','-p','no:cacheprovider'],1)]:
            start=time.monotonic();r=subprocess.run([sys.executable,*args],cwd=root,env=env,capture_output=True,text=True,timeout=180)
            blob=r.stdout+r.stderr;(raw/(name+'.log')).write_text(blob)
            public=blob.replace(str(here),'<NEW_PROBE_DIR>').replace(str(root),'<PINNED_CHECKOUT>')
            (out/(name+'.log')).write_text(public)
            row={'name':name,'command':['python',*['<RESULTS>/'+Path(x).name if x.startswith(str(out)) else '<NEW_PROBE_DIR>/'+Path(x).name if x.startswith(str(here)) else x for x in args]],'exit_code':r.returncode,'seconds':round(time.monotonic()-start,3),'raw_sha256':hashlib.sha256(blob.encode()).hexdigest(),'published_sha256':hashlib.sha256(public.encode()).hexdigest()};records.append(row)
            print(json.dumps(row),flush=True);assert r.returncode==expected,public
            if name=='safety-acceptance':assert '6 failed, 1 passed' in r.stdout,public
    status=subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True);after=hashlib.sha256((root/'data/memelab.sqlite').read_bytes()).hexdigest()
    assert status=='' and before==after and network.read_text()==''
    record={'classification':'NEW_REPLICATION_NOT_RECOVERED_PHASE03_EXECUTION','application_sha':PIN,'checks':records,'network_events':0,'tracked_database_before':before,'tracked_database_after':after,'final_checkout_status':status,'python':sys.version,'per_check_timeout_seconds':180,'extra_memory_cap':'none','resource_termination':False,'source_hashes':{name:hashlib.sha256((here/name).read_bytes()).hexdigest() for name in ['inputs.json','probe_cases.py','test_safety_acceptance.py','run_replication.py']}}
    (out/'execution.json').write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':main()
