"""Overlay source on verified memory images; no generative runtime or assets."""
import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
PARENTS={'base':('fusion-single-node:memory-base-v6','sha256:37036c320f75c2d714993ca319cbf1c72ed55ac2f7d35946d4edad74b9d5cb70'),'caller':('fusion-memory-caller:memory-v6','sha256:fac86105a864e4ce101d312a935eef808c6015d3513eaa47be79cd32acea3c9a'),'embedding':('fusion-memory-embedding:memory-v6','sha256:9007d658d3ec76ea8f7b00e331dbdbbdd5fe9794c46bf4d36958a5f7c60e4550')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('destination',type=Path);p.add_argument('--kind',choices=PARENTS,required=True);a=p.parse_args();base,pin=PARENTS[a.kind]
 actual=subprocess.check_output(['docker','image','inspect',base,'--format','{{.Id}}'],text=True).strip();assert actual==pin
 a.destination.mkdir(parents=True,exist_ok=False);source=a.destination/'source';source.mkdir();files={}
 for folder in ('fusion','integration'):
  for file in sorted((ROOT/folder).rglob('*')):
   if file.is_file() and '__pycache__' not in file.parts and file.suffix in ('.py','.json','.metta'):
    rel=file.relative_to(ROOT);dest=source/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,dest);files[str(rel)]=sha(file)
 irc=ROOT/'artifacts/s06/ngircd/sbin/ngircd';assert irc.is_file() and sha(irc)=='b29b4c31e8f515062f2ed814b01c1774da2b6a1f3e099d6e316e8d3489ff3f74';shutil.copyfile(irc,a.destination/'ngircd');(a.destination/'ngircd').chmod(0o755)
 (a.destination/'Dockerfile').write_text(f'FROM {base}\nUSER root\nCOPY source /opt/fusion\nCOPY ngircd /opt/irc/sbin/ngircd\nUSER 1000:1000\n')
 (a.destination/'package.json').write_text(json.dumps(dict(parent=base,parent_config=pin,source=files,ngircd_sha256=sha(irc),kind=a.kind),indent=2)+'\n')
if __name__=='__main__':main()
