#!/usr/bin/env python3
"""Create fresh isolated-demo TLS/auth Secrets, separately from Helm.

Never prints credentials or puts them in chart values. Not a production PKI.
Explicit kubeconfig and namespace prevent touching the developer's cluster.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess

ROLES=('omega-agent','fusion-execution','fusion-storage','fusion-messaging')


def main():
    p=argparse.ArgumentParser();p.add_argument('--kubeconfig',required=True)
    p.add_argument('--workflow',action='store_true');p.add_argument('--memory',action='store_true');p.add_argument('--namespace',required=True);p.add_argument('--directory',required=True);a=p.parse_args()
    a.memory=a.memory or a.workflow
    root=Path(a.directory).resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False)
    os.umask(0o077)
    def openssl(*args):subprocess.run(['openssl',*map(str,args)],cwd=root,check=True,capture_output=True)
    (root/'ca.cnf').write_text('[req]\ndistinguished_name=dn\nx509_extensions=ca\n[dn]\n[ca]\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\n')
    openssl('req','-x509','-newkey','rsa:2048','-nodes','-keyout','ca.key','-out','ca.crt','-days','7',
            '-subj','/CN=synthetic-single-node-ca','-config','ca.cnf')
    roles=ROLES+(('fusion-search','fusion-embedding') if a.memory else ())
    if a.workflow:roles+=('fusion-model','fusion-channel-bridge','irc-server','irc-peer')
    source_token=secrets.token_hex(32)
    measured={r:secrets.token_hex(32) for r in ('fusion-storage','fusion-search','fusion-embedding')}
    channel={r:{p:secrets.token_hex(32) for p in ('M','bridge')} for r in ('storage','messaging')}
    delegated={p:secrets.token_hex(32) for p in ('M','bridge')}
    client={r:secrets.token_hex(32) for r in roles[1:]}
    worker={r:secrets.token_hex(32) for r in roles[1:]}
    for role in roles:
        dns=f'{role}.{a.namespace}.svc.cluster.local'
        # X.509 CN has a 64-byte limit; hostname verification uses the complete
        # DNS SAN below, including long but valid Kubernetes namespaces.
        openssl('req','-newkey','rsa:2048','-nodes','-keyout',role+'.key','-out',role+'.csr','-subj','/CN='+role)
        (root/'extensions').write_text(f'subjectAltName=DNS:{dns}\nextendedKeyUsage=serverAuth\nbasicConstraints=critical,CA:FALSE\n')
        openssl('x509','-req','-in',role+'.csr','-CA','ca.crt','-CAkey','ca.key','-CAcreateserial',
                '-out',role+'.crt','-days','7','-extfile','extensions')
        openssl('verify','-CAfile','ca.crt',role+'.crt')
        data={name:(root/file).read_bytes() for name,file in [('ca.crt','ca.crt'),('tls.crt',role+'.crt'),('tls.key',role+'.key')]}
        if role=='omega-agent':data.update({r+'-token':v.encode() for r,v in client.items()})
        else:
            data.update({'caller-token':client[role].encode(),'worker-token':worker[role].encode()})
            if role=='fusion-execution':data.update({r+'-token':worker[r].encode() for r in ROLES[2:]})
        if a.memory and role in ('fusion-storage','fusion-search'):
            data['indexer-token']=(source_token if role=='fusion-storage' else secrets.token_hex(32)).encode()
            if role=='fusion-search':data['storage-source-token']=source_token.encode()
        if a.workflow:
            if role in measured:data['measured-token']=measured[role].encode()
            if role=='omega-agent':
                data.update({'measured-'+r+'-token':v.encode() for r,v in measured.items()})
            if role in ('omega-agent','fusion-channel-bridge'):
                actor='M' if role=='omega-agent' else 'bridge'
                data.update({'channel-'+r+'-token':v[actor].encode() for r,v in channel.items()})
            if role in ('fusion-storage','fusion-messaging'):
                r=role.removeprefix('fusion-')
                data.update({'channel-caller-token':channel[r]['M'].encode(),'channel-bridge-token':channel[r]['bridge'].encode()})
                data.update({'payload-'+p+'-token':v.encode() for p,v in delegated.items()})
            if role=='fusion-model':data['other-token']=secrets.token_hex(32).encode()
            if role in ('omega-agent','fusion-channel-bridge','irc-server','irc-peer'):
                data.pop('tls.key');data.pop('tls.crt')
        value=dict(apiVersion='v1',kind='Secret',metadata=dict(name=role+'-tls-auth',namespace=a.namespace),
                   type='Opaque',data={k:base64.b64encode(v).decode() for k,v in data.items()})
        (root/(role+'.secret.json')).write_text(json.dumps(value))
        subprocess.run(['kubectl','--kubeconfig',a.kubeconfig,'create','-f','-'],input=json.dumps(value),text=True,check=True)
    print('Created '+str(len(roles))+' existing Secret references; private material remains in '+str(root))


if __name__=='__main__':main()
