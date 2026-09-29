"""Run from the repository root. Read-only audit checks; writes only report if asked."""
from pathlib import Path
import datetime,hashlib,json,re,subprocess,sys
root=Path.cwd();D=root/'docs';HERE=Path(__file__).resolve().parent;E=HERE.parent/"closure-5b56328"
errors=[]
sources=json.loads((E/'utility-sources.json').read_text())
inv=json.loads((E/'utility-inventory.json').read_text())
assert len(sources['pages'])==len({x['utility'] for x in sources['pages']})==155
assert all(x['status']==0 and x['sha256'] for x in sources['pages'])
entries=inv['entries'];assert len(entries)==len({x['name'] for x in entries})==156
assert {x['name'] for x in entries}=={x['utility'] for x in sources['pages']}|{'['}
assert sum(x['scope']=='base' for x in entries)==111
assert sum(x['exec_required'] for x in entries)==101
assert all(x['owner'] for x in entries if x['scope']=='base')
assert next(x for x in entries if x['name']=='ar')['scope']=='conditional SD'
for name in ['mailx','crontab','df','kill','ls','ps','sh','tabs','ulimit','who','xargs']:
 assert next(x for x in entries if x['name']==name)['scope']=='base'
for r in json.loads((E/'defect-dispositions.json').read_text())['records']:
 for x in r['evidence']:
  b=(root/x['path']).read_bytes();assert hashlib.sha256(b).hexdigest()==x['sha256'] and len(b)==x['bytes'],x['path']
 # All current strict regression paths exist, independent of original source identity.
 for source in r['coverage'].split('; '):assert (root/source.split(':')[0]).exists(),source
for name in ['src','include','tests','tools','Makefile','Dockerfile','.github/workflows']:
 diff=subprocess.check_output(['git','diff','008c1f9','--',name],text=True)
 assert not diff,name
# Check every local Markdown link in modified/new documents against baseline.
files=subprocess.check_output(['git','diff','--name-only','c8c1c91'],text=True).splitlines()+subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()
files=sorted(set(x for x in files if x.endswith('.md')))
def anchors(p):
 s=p.read_text();result=set(re.findall(r'<a\s+(?:name|id)="([^"]+)"',s));seen={}
 for h in re.findall(r'^#+\s+(.+)$',s,re.M):
  h=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',h).replace('`','').lower()
  a=re.sub(r'[^\w\- ]','',h).replace(' ','-');n=seen.get(a,0);seen[a]=n+1;result.add(a+('-'+str(n) if n else ''))
 return result
links=0
for name in files:
 p=root/name
 for target in re.findall(r'\]\(([^\s)]+)\)',p.read_text()):
  if target.startswith(('http:','https:','mailto:','codex:','app:')):continue
  bits=target.split('#',1);dest=(p.parent/bits[0]).resolve() if bits[0] else p;links+=1
  if not dest.exists():errors.append([name,target,'missing'])
  elif len(bits)>1 and dest.suffix=='.md' and bits[1] not in anchors(dest):errors.append([name,target,'anchor'])
# Both ownership directions remain in sync; old raw artifacts retain their hashes.
audit=subprocess.run([sys.executable,str(D/'evidence/csh-012/integrated-07ee1cb/audit.py')],capture_output=True,text=True)
assert audit.returncode==0,audit.stdout+audit.stderr
owned=json.loads(audit.stdout)
report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'utility_counts':inv['counts'],'dispositions':11,'source_fixture_workflow_match_integration_base':'008c1f9','markdown_files':len(files),'local_links':links,'link_errors':errors,'requirement_families':owned['requirement_count'],'ownership_pairs':owned['forward_reverse_pairs'],'artifact_entries_checked':owned['artifact_entries'],'unexplained_artifact_drift':owned['unexplained_mismatches']}
print(json.dumps(report,indent=2))
if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(bool(errors))
