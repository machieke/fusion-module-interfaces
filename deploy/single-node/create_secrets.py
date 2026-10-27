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
    p.add_argument('--namespace',required=True);p.add_argument('--directory',required=True);a=p.parse_args()
    root=Path(a.directory).resolve();root.mkdir(mode=0o700,parents=True,exist_ok=False)
    os.umask(0o077)
    def openssl(*args):subprocess.run(['openssl',*map(str,args)],cwd=root,check=True,capture_output=True)
    (root/'ca.cnf').write_text('[req]\ndistinguished_name=dn\nx509_extensions=ca\n[dn]\n[ca]\nbasicConstraints=critical,CA:TRUE\nkeyUsage=critical,keyCertSign,cRLSign\nsubjectKeyIdentifier=hash\n')
    openssl('req','-x509','-newkey','rsa:2048','-nodes','-keyout','ca.key','-out','ca.crt','-days','7',
            '-subj','/CN=synthetic-single-node-ca','-config','ca.cnf')
    client={r:secrets.token_hex(32) for r in ROLES[1:]}
    worker={r:secrets.token_hex(32) for r in ROLES[1:]}
    for role in ROLES:
        dns=f'{role}.{a.namespace}.svc.cluster.local'
        openssl('req','-newkey','rsa:2048','-nodes','-keyout',role+'.key','-out',role+'.csr','-subj','/CN='+dns)
        (root/'extensions').write_text(f'subjectAltName=DNS:{dns}\nextendedKeyUsage=serverAuth\nbasicConstraints=critical,CA:FALSE\n')
        openssl('x509','-req','-in',role+'.csr','-CA','ca.crt','-CAkey','ca.key','-CAcreateserial',
                '-out',role+'.crt','-days','7','-extfile','extensions')
        openssl('verify','-CAfile','ca.crt',role+'.crt')
        data={name:(root/file).read_bytes() for name,file in [('ca.crt','ca.crt'),('tls.crt',role+'.crt'),('tls.key',role+'.key')]}
        if role=='omega-agent':data.update({r+'-token':v.encode() for r,v in client.items()})
        else:
            data.update({'caller-token':client[role].encode(),'worker-token':worker[role].encode()})
            if role=='fusion-execution':data.update({r+'-token':worker[r].encode() for r in ROLES[2:]})
        value=dict(apiVersion='v1',kind='Secret',metadata=dict(name=role+'-tls-auth',namespace=a.namespace),
                   type='Opaque',data={k:base64.b64encode(v).decode() for k,v in data.items()})
        (root/(role+'.secret.json')).write_text(json.dumps(value))
        subprocess.run(['kubectl','--kubeconfig',a.kubeconfig,'create','-f','-'],input=json.dumps(value),text=True,check=True)
    print('Created four existing Secret references; private material remains in '+str(root))


if __name__=='__main__':main()
