"""Package verified offline remediations; never fetch during Docker build."""
import hashlib,json,shutil
from pathlib import Path


def prepare(root,destination,directory):
    if directory is None:return ''
    directory=Path(directory).resolve();lock=root/'integration/neoclaw/pilot-leaf-remediation.json'
    selected=json.loads(lock.read_bytes());target=destination/'remediation';target.mkdir()
    assert selected['profile']=='compatible-sdk-leaf-remediation/1'
    for row in selected['packages']:
        source=directory/'wheels'/row['filename']
        assert source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest()==row['sha256']
        shutil.copyfile(source,target/row['filename'])
    debs=directory/'debs';layer=''
    if debs.exists():
        meta=json.loads((directory/'debs.json').read_bytes());(target/'debs').mkdir()
        for row in meta['files']:
            source=debs/row['file'];assert source.name==row['file'] and hashlib.sha256(source.read_bytes()).hexdigest()==row['sha256']
            shutil.copyfile(source,target/'debs'/row['file'])
        assert meta['files'];shutil.copyfile(directory/'debs.json',target/'debs.json')
        layer='RUN env PATH=/usr/sbin:/usr/bin:/sbin:/bin dpkg -i /opt/pilot-remediation-wheels/debs/*.deb\n'
    return ('COPY remediation /opt/pilot-remediation-wheels\n'+layer+
        'RUN PYTHONPATH=/opt/fusion /opt/native/python/bin/python3.12 -m integration.single_node.pilot_remediation /opt/pilot-remediation-wheels\n')
