"""Bounded, non-mutating owner-local counters. No payloads, refs or credentials.

Run in each service pod through operator RBAC. This is not a privileged module
port, and never opens another owner's PVC. SQLite reads use read-only snapshots.
"""
import argparse,json,os,sqlite3
from pathlib import Path

FILES={
 'measured.sqlite':('app_occurrences','app_memory_reads','app_query_vectors','app_model_calls','app_channel_inputs','app_channel_outputs'),
 'bridge.sqlite':('channel_ingress','channel_egress'),
 'channel-messages.sqlite':('messages',),
 'commitments.sqlite':('m4_intent','m4_observations'),
 'chain-progress.sqlite':('progress',),
 'caller.sqlite':('app_occurrences','app_memory_writes','app_memory_reads','app_query_vectors','app_memory_vectors','app_sources','app_assessments','app_priority','caller_requests'),
 'execution.sqlite':('jobs','s01_work','outbox'),
 'atoms.sqlite':('atoms',), 'messages.sqlite':('messages','acknowledgements'),
 'model.sqlite':('model_calls',),'encoder.sqlite':('encode_attempts','encode_intents'),
 'memory/feed.sqlite':('feed_atoms',),'channel.sqlite':('messages','acknowledgements'),
 'cognitive/episodes.sqlite':('episodes','events','deliveries','completions'),
 'cognitive/beliefs.sqlite':('snapshots','attempts','nal_budgets','nal_priors'),
 'cognitive/relay.sqlite':('deliveries',), 'cognitive/attention.sqlite':('contexts','history','bindings'),
 'cognitive/relations.sqlite':('accepted','commands','incidence'),
 'cognitive/exact-search.sqlite':('records','rebuilds'),
 'cognitive/cognitive-atoms.sqlite':('feed_atoms',)}
COLUMNS=('done','acknowledged','sent','reserved','attempts','calls','builds','queries','evaluations','finished','linked','visible')
PRESENT=('result','response','view','receipt','output','decision','signed')

def inspect(root=Path('/state')):
 out=dict(owner='UNKNOWN',tables={},status={},limits=dict(max_database_files=len(FILES),max_tables=sum(map(len,FILES.values()))),live_generation_activity='NOT_INFERRED_FROM_DIAGNOSTICS')
 seal=root/'owner-seal.json'
 if seal.is_file():
  raw=json.loads(seal.read_bytes());out['owner']=raw['role'];out['composition']=raw['composition']
 for name,names in FILES.items():
  path=root/name
  if not path.is_file():continue
  with sqlite3.connect(path.absolute().as_uri()+'?mode=ro',uri=True,timeout=.2) as db:
   db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
   tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
   for table in names:
    if table not in tables:continue
    columns={r[1] for r in db.execute('PRAGMA table_info("'+table+'")')}
    fields={'rows':db.execute('SELECT count(*) FROM "'+table+'"').fetchone()[0]}
    for col in COLUMNS:
     if col in columns:fields[col+'_sum']=db.execute('SELECT coalesce(sum("'+col+'"),0) FROM "'+table+'"').fetchone()[0]
    for col in PRESENT:
     if col in columns:fields[col+'_captured']=db.execute('SELECT count(*) FROM "'+table+'" WHERE "'+col+'" IS NOT NULL').fetchone()[0]
    if 'failure_code' in columns:
     known=('NOT_AVAILABLE','INVALID_ARGUMENT','UNSUPPORTED_PROFILE','DEADLINE_EXCEEDED','UNAUTHORIZED','OVERLOADED','CONFLICT')
     for code in known:fields['failure_'+code]=db.execute('SELECT count(*) FROM "'+table+'" WHERE failure_code=?',(code,)).fetchone()[0]
    out['tables'][name+':'+table]=fields
 for name in ('native-status.json','measured-status.json','worker-status.json','shutdown.json'):
  path=root/name
  if path.is_file():
   raw=json.loads(path.read_bytes());out['status'][name]={k:raw[k] for k in ('status','code') if k in raw}
 publication=root/'memory/search/published.json'
 if publication.is_file():
  value=json.loads(publication.read_text());out['search_publication']=dict(retained_generations=len(value.get('generations',{})),source_heads=[v.get('head',{}).get('sequence') for v in value.get('generations',{}).values()] if isinstance(value.get('generations'),dict) else [])
 final=root/'final-observation.json'
 if final.is_file():
  value=json.loads(final.read_text());value=value.get('detail',{}).get('chain',value);out['chain']={k:value[k] for k in ('submission','inclusion','execution','effect','effect_finality') if k in value and isinstance(value[k],(str,bool,int,type(None)))}
 out['restore_fenced']=(root/'restore-fence.json').is_file()
 out['process_rss_bytes']=int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
 return out

def metrics(value):
 # Label values come only from fixed filenames/table names and the fixed role.
 lines=['# TYPE fusion_owner_rows gauge','# TYPE fusion_owner_observation gauge']
 for table,fields in value['tables'].items():
  for key,count in fields.items():
   metric='fusion_owner_rows' if key=='rows' else 'fusion_owner_observation'
   lines.append(f'{metric}{{owner="{value["owner"]}",table="{table}",stage="{key}"}} {count}')
 return '\n'.join(lines)+'\n'
def main():
 p=argparse.ArgumentParser();p.add_argument('--metrics',action='store_true');a=p.parse_args();v=inspect();print(metrics(v) if a.metrics else json.dumps(v,sort_keys=True))
if __name__=='__main__':main()
