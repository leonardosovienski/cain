"""Finite CAIN public CLI evaluation harness, no model, shell, scheduler or self-grants."""
import argparse, hashlib, json, os, pathlib, signal, subprocess, sys, time, threading, re
B=pathlib.Path(__file__).parent
cancelled=False
quota=None

class ResourceLimit(ValueError):
 pass

def used(directory):
 return sum(p.stat().st_size for p in directory.iterdir() if p.is_file())
def cancel(signum,frame):
 global cancelled
 cancelled=True
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
def save(path,value,control=True):
 raw=canonical(value)
 if quota is not None:
  ceiling=quota if control else quota-min(16384,quota//2)
  if used(path.parent)+len(raw)>ceiling:raise ResourceLimit('RUN_BYTES_CAP')
 temp=path.with_suffix('.tmp')
 with temp.open('wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 os.replace(temp,path)
def run(config_path, state_dir, stop_after=None):
 global cancelled, quota
 cancelled=False
 config=json.loads(config_path.read_bytes()); state_dir.mkdir(parents=True,exist_ok=True)
 quota=config['max_run_bytes']
 if type(quota) is not int or quota<4096:raise ValueError('Invalid storage quota')
 ids=[c['case_id'] for c in config['cases']]
 if len(ids)!=len(set(ids)) or any(not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',i) for i in ids):raise ValueError('Invalid case IDs')
 if used(state_dir)+32>quota:raise ResourceLimit('EXISTING_STATE_OVER_CAP')
 lock=state_dir/'runner.lock'
 with lock.open('x') as f:f.write(str(os.getpid()))
 state={}; active=None; authenticated=False
 try:
  if len(config_path.read_bytes())>min(1000000,quota//4):raise ResourceLimit('CONFIG_BYTES_CAP')
  policy=pathlib.Path(config['policy']); db=pathlib.Path(config['db'])
  if not db.is_file() or not policy.is_file():raise ValueError('Missing preexisting corpus/policy')
  from cain.evaluation.resources import installed_identity
  from cain.research import ResearchService
  from cain.research.bundles import BundleService
  service=ResearchService(db,policy); bundles=BundleService(service)
  fingerprint={}
  for domain in config['collections']:
   scope=service.scope('leo',None,domain); bundles.verify(scope)
   with service.connection() as snapshot_db:
    snapshot_db.execute('BEGIN')
    q=bundles.query(scope,limit=50,_db=snapshot_db)
    count=max(q['total'],q['artifact_total'],q['evidence_total'],q['relation_total'])
    if count>config['max_cardinality']:raise ValueError('Cardinality cap')
    for offset in range(50,count,50):
     page=bundles.query(scope,limit=50,offset=offset,_db=snapshot_db)
     for field in ('entities','artifacts','relations','evidence'):q[field].extend(page[field])
   fingerprint[domain]=sha(canonical(q))
  identity=dict(code=installed_identity()['source_tree_sha256'],runner=sha(pathlib.Path(__file__).read_bytes()),policy=sha(policy.read_bytes()),corpus=fingerprint,config=sha(config_path.read_bytes()))
  if identity['code'] != config['expected_code'] or identity['policy'] != config['expected_policy']:
   raise ValueError('CANDIDATE_OR_POLICY_CHANGED')
  checkpoint=state_dir/'CHECKPOINT.json'
  if checkpoint.exists():
   state=json.loads(checkpoint.read_bytes())
   if state['identity']!=identity:raise ValueError('STATE_CHANGED: preserve checkpoint; revalidate and use a new run directory')
   for item in state['completed'].values():
    if sha((state_dir/item['result']).read_bytes()) != item['sha256']:
     raise ValueError('COMPLETED_RESULT_CORRUPTION')
  else:state=dict(identity=identity,status='RUNNING',completed={},model_calls=0,actor='CODEX_ENGINEERING_HARNESS',method='deterministic',resource_usage=dict(max_rss='UNKNOWN',model_tokens='NOT_APPLICABLE'))
  authenticated=True
  state['status']='RUNNING';save(checkpoint,state)
  started=time.monotonic(); rounds=0
  for case in config['cases']:
   if case['case_id'] in state['completed']:continue
   if cancelled:state['status']='CANCELLED';break
   if rounds>=config['max_cases_per_run'] or time.monotonic()-started>=config['max_seconds']:state['status']='LIMIT_REACHED';break
   if used(state_dir)+config['max_output_bytes']>config['max_run_bytes']:state['status']='LIMIT_REACHED';break
   if __import__('shutil').disk_usage(state_dir).free<config['reserve_bytes']:state['status']='LIMIT_REACHED';break
   cmd=[sys.executable,'-m','cain','research','--db',str(db),'--policy',str(policy),'--user','leo','--collection',case['collection'],'bundle',*case['args']]
   target=state_dir/(case['case_id']+'.json')
   before=time.monotonic()
   output=bytearray();errors=bytearray(); output_lock=threading.Lock(); exceeded=threading.Event()
   def drain(pipe,destination):
    with pipe:
     while True:
      chunk=pipe.read(4096)
      if not chunk:break
      with output_lock:
       remaining=config['max_output_bytes']-len(output)-len(errors)
       destination.extend(chunk[:remaining])
       if len(chunk)>remaining:exceeded.set()
   active=subprocess.Popen(cmd,cwd=B,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
   readers=[threading.Thread(target=drain,args=(active.stdout,output)),threading.Thread(target=drain,args=(active.stderr,errors))]
   for reader in readers:reader.start()
   while active.poll() is None:
     if cancelled or time.monotonic()-before>config['subprocess_seconds'] or exceeded.is_set():
      active.terminate()
      try:active.wait(timeout=5)
      except subprocess.TimeoutExpired:active.kill();active.wait(timeout=5)
      break
     time.sleep(.05)
   for reader in readers:reader.join(timeout=5)
   if any(reader.is_alive() for reader in readers):raise ValueError('OUTPUT_READER_DID_NOT_STOP')
   code=active.returncode;active=None
   if cancelled:state['status']='CANCELLED';save(checkpoint,state);break
   if exceeded.is_set():raise ResourceLimit('OUTPUT_CAP')
   actual=json.loads(output) if code==0 else None
   passed=code==0 and all(actual.get(k)==v for k,v in case['expected'].items())
   result=dict(case=case,candidate=identity['code'],corpus_snapshot=identity['corpus'],policy=identity['policy'],command=cmd,method='deterministic',actual_cain_output=actual,exit_code=code,latency_seconds=time.monotonic()-before,status='PASS' if passed else 'FAIL',limitation='Oracle checks declared counts/status only, not semantic entailment or economic truth')
   result['stderr']=errors.decode(errors='replace')
   entry=dict(result=target.name,sha256=sha(canonical(result)),status=result['status'])
   prospective=dict(state,completed=dict(state['completed'],**{case['case_id']:entry}))
   if used(state_dir)+len(canonical(result))+2*len(canonical(prospective))+1024>quota:
    raise ResourceLimit('RESULT_AND_CHECKPOINT_CAP')
   save(target,result,control=False);state['completed'][case['case_id']]=entry
   rounds+=1;save(checkpoint,state)
   if stop_after is not None and rounds>=stop_after:state['status']='CANCELLED';break
  else:state['status']='COMPLETED' if all(x['status']=='PASS' for x in state['completed'].values()) else 'FAILED'
  save(checkpoint,state)
  print(json.dumps(dict(status=state['status'],completed=len(state['completed']),checkpoint=str(checkpoint))))
  return 0 if state['status']=='COMPLETED' else 2
 except ResourceLimit as exc:
  state['status']='LIMIT_REACHED';state['limit_reason']=str(exc)
  save(state_dir/('CHECKPOINT.json' if authenticated else 'LAST_LIMIT.json'),state)
  return 2
 except BaseException as exc:
  # Never overwrite an earlier identity/checkpoint on a mismatch.
  save(state_dir/'LAST_FAILURE.json',dict(type=type(exc).__name__,reason=str(exc),status='FAILED'))
  raise
 finally:
  if active is not None and active.poll() is None:active.terminate();active.wait(timeout=5)
  lock.unlink(missing_ok=True)
if __name__=='__main__':
 signal.signal(signal.SIGINT,cancel);signal.signal(signal.SIGTERM,cancel)
 p=argparse.ArgumentParser();p.add_argument('--config',type=pathlib.Path,required=True);p.add_argument('--state',type=pathlib.Path,required=True);p.add_argument('--stop-after',type=int)
 a=p.parse_args();sys.exit(run(a.config,a.state,a.stop_after))
