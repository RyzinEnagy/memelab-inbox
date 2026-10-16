import sys,os
for k in list(os.environ):
 if any(s in k.upper() for s in ('TOKEN','API_KEY','PASSWORD','SECRET')): os.environ.pop(k,None)
def guard(event,args):
 if event in ('socket.connect','socket.getaddrinfo'):
  with open(os.environ['AUDIT_NETWORK_LOG'],'a') as f: f.write(event+'\n')
  raise RuntimeError('AUDIT: network disabled')
sys.addaudithook(guard)
