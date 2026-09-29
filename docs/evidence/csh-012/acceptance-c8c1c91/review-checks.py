"""Run from the repository root before committing this review.

Checks changed/untracked Markdown, baseline source identities and CI snapshot.
A post-commit invocation has a smaller changed-document set; use the retained
JSON for the original pre-commit scope.
"""
from pathlib import Path
import subprocess,re,json,hashlib,datetime,gzip
root=Path.cwd();changed=subprocess.check_output(['git','diff','--name-only'],text=True).splitlines()+subprocess.check_output(['git','ls-files','--others','--exclude-standard'],text=True).splitlines()
md=[root/x for x in changed if x.endswith('.md')]
def anchors(p):
 text=p.read_text();out=set(re.findall(r'<a\s+(?:name|id)="([^"]+)"',text));seen={}
 for h in re.findall(r'^#+\s+(.+)$',text,re.M):
  h=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',h).replace('`','').lower()
  a=re.sub(r'[^\w\- ]','',h).replace(' ','-');n=seen.get(a,0);seen[a]=n+1
  out.add(a+('-'+str(n) if n else ''))
 return out
errors=[];links=0
for p in md:
 for target in re.findall(r'\]\(([^\s)]+)\)',p.read_text()):
  if target.startswith(('http:','https:','mailto:','codex:','app:')):continue
  parts=target.split('#',1);dest=(p.parent/parts[0]).resolve() if parts[0] else p
  links+=1
  if not dest.exists():errors.append([str(p.relative_to(root)),target,'missing path'])
  elif len(parts)>1 and dest.suffix=='.md' and parts[1] not in anchors(dest):errors.append([str(p.relative_to(root)),target,'missing anchor'])
# Existing inbound links to renamed section anchors.
for p in [root/'README.md',root/'CONTRIBUTING.md',*root.glob('docs/**/*.md')]:
 for target in re.findall(r'\]\(([^\s)]+)\)',p.read_text()):
  if 'architecture.md#target-module-boundaries' in target or 'implementation-plan.md#first-parallel-work' in target:
   errors.append([str(p.relative_to(root)),target,'renamed incoming anchor'])
# Require every mapped source path to exist and unchanged production/workflow bytes.
identity=json.loads((root/'docs/evidence/csh-012/acceptance-c8c1c91/native-identity.json').read_text())
source_matches=all(hashlib.sha256((root/name).read_bytes()).hexdigest()==digest for name,digest in identity['source_manifest'].items())
assert source_matches
base='c8c1c91372e6e77cf2e7032765cd3c068fa1906d'
diagrams=True
for p in md:
 rel=str(p.relative_to(root))
 old=subprocess.run(['git','show',base+':'+rel],capture_output=True,text=True)
 if old.returncode==0:
  diagrams &= re.findall(r'```mermaid\n.*?```',old.stdout,re.S)==re.findall(r'```mermaid\n.*?```',p.read_text(),re.S)
assert diagrams
ci=json.loads((root/'docs/evidence/csh-012/acceptance-c8c1c91/ci.json').read_text())
assert ci['headSha']==base and ci['conclusion']=='success' and all(j['conclusion']=='success' for j in ci['jobs'])
report={'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'markdown_files_checked':len(md),'local_links_checked':links,'errors':errors,'production_source_hashes_match_baseline':source_matches,'mermaid_diagrams_unchanged':diagrams,'baseline_ci_all_three_jobs_success':True}
print(json.dumps(report,indent=2))
(root/'docs/evidence/csh-012/acceptance-c8c1c91/review-checks.json').write_text(json.dumps(report,indent=2)+'\n')
raise SystemExit(bool(errors))
