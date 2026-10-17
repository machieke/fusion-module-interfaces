"""Build all standalone module presentations; no integration or benchmark is run."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import zipfile

import catalogue
import render
from render import base, C, Slide, band, table, note, width

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
QA = ROOT / 'artifacts/presentation-modules-qa'
GROUPS = [
    ('Persistence', [0, 1, 13]),
    ('Knowledge access', [2, 3]),
    ('Cognition', [4, 5, 6, 7, 8]),
    ('Coordination + policy', [9, 10, 11, 12, 14]),
]
SHORT = ['DA storage','AtomStorage · C0','Relations','Search projection','Episodes · C1',
         'Beliefs · C2','PLNKernel','Attention · C3','Inference · C4','Messaging',
         'Execution','Registry','Resolver','ConsensusFinality','Authorization']


def fit_text(s, x, y, w, text, size=36, color=None, style='bold'):
    while width(text, size, style) > w:
        size -= 1
    return s.text(x,y,w,text,size,color,style)


def source_note(m, text):
    links = ', '.join(f'[{Path(p).name}](https://github.com/machieke/fusion-module-interfaces/blob/{catalogue.SOURCE_COMMIT}/{p})' for p in m['sources'])
    return text + '\n\nEvidence and implementation: ' + links + '.\n\n' + (
        'Scope: repository snapshot ' + catalogue.SOURCE_COMMIT + '; tested M5 runtime ' + catalogue.TESTED_COMMIT +
        '. Historical observations keep their own milestone source. This deck build runs no runtime or benchmark. '
        'Future directions and proposed benchmark designs are not implemented work or measured results.')


def make_slide(m, title, section, subtitle='', dark=False):
    s=Slide(title,section,subtitle,source=m['name']+' · M5 source bfb0ec8',dark=dark)
    return s


def build_module(m):
    base.SLIDES.clear()
    color=m['color']
    s=make_slide(m,m['name'],'Omega × ASI / standalone module series',dark=True)
    s.text(72,234,1450,m['thesis'],64,C['white'],'bold',1.15)
    s.tag(76,421,'ELI16 · THE IDEA IN PLAIN LANGUAGE',color,C['mint'] if color=='teal' else C['ice'],18)
    s.text(76,479,1410,m['analogy'],32,C['white'])
    s.text(76,621,1410,'Why it matters: '+m['why'],28,C['dim'])
    s.text(76,790,1370,'Through M5 · 17 October 2026 · 12–15 minute talk · evidence and proposals kept separate',19,C['dim'])
    note(s,source_note(m,'Open with the analogy, then state the technical responsibility: '+m['role']+' '+m['why']+' Do not treat the analogy as an additional experiment. This is a standalone talk about one responsibility, not a claim that every module is a separate service or repository.'))

    s=make_slide(m,'One module in a system of fifteen','01 / Helicopter view',
                 'The highlighted responsibility is the subject of this talk; placement and process count are separate decisions.')
    index=catalogue.MODULES.index(m)
    for col,(group,items) in enumerate(GROUPS):
        x=72+col*370
        s.rect(x,236,346,468,C['pale'],radius=14)
        fit_text(s,x+18,255,310,group,23,C['muted'])
        for row,item in enumerate(items):
            selected=item==index;y=309+row*73
            s.rect(x+15,y,316,59,C[color] if selected else C['white'],radius=8)
            fit_text(s,x+28,y+15,290,SHORT[item],24,C['white'] if selected else C['ink'])
    s.text(80,728,1430,m['role'],27,C['ink'])
    note(s,source_note(m,'Locate '+m['name']+' in the bounded fifteen-family inventory. The grey groups are explanatory categories, not deployment units. RevisionMath, the evidence relay, native plugins and transport bindings are supporting seams rather than additional module families. Registry and Resolver are separate responsibilities even though both are implemented in registry.py. Fifteen represented families is not full Omega requirements coverage. '+m['dependency_note']))

    s=make_slide(m,'Dependencies explain the boundary','02 / Function dependencies',
                 'Arrows point from caller to dependency. Stores and runtime internals are labelled explicitly.')
    s.box(72,322,375,219,m['caller'],m['calls'],color,'white',title_size=29,body_size=25)
    s.box(555,322,425,219,m['name'],m['role'],color,'mint' if color=='teal' else 'ice',title_size=33,body_size=25)
    s.line(447,431,555,431,C[color],arrow=True)
    n=len(m['dependencies']); h=132; start=218 if n==4 else 260
    for i,(title,body) in enumerate(m['dependencies']):
        y=start+i*(137 if n==4 else 157)
        s.box(1103,y,425,h,title,body,color,'white',title_size=27,body_size=23)
        s.path([(980,431),(1036,431),(1036,y+h/2),(1103,y+h/2)],C[color])
    band(s,'One responsibility does not imply one process. A dependency does not grant access to its private tables.',size=25)
    note(s,source_note(m,m['dependency_note']+' The left node is a caller or caller class; the right nodes distinguish foreign ports, pure helpers, local state and runtime internals. There is no implied shared transaction. '+m['excludes'][0][1]+'.'))

    s=make_slide(m,'Responsibility, state and scope','03 / Ownership',
                 'The owner is authoritative for its own state; other responsibilities are deliberately separate.')
    for x,heading,items,fill in [(72,'OWNS / GUARANTEES',m['owns'],'ice'),(816,'OUTSIDE THIS RESPONSIBILITY',m['excludes'],'sand')]:
        s.text(x+12,233,690,heading,20,C['blue'] if fill=='ice' else C['amber'],'bold')
        for i,(title,body) in enumerate(items):
            s.box(x,280+i*214,712,190,title,body,'blue' if fill=='ice' else 'amber',fill,title_size=31,body_size=26)
    band(s,m['profile'],size=25)
    note(s,source_note(m,'State ownership is the key contract, not the file layout. '+ ' '.join(t+': '+b+'.' for t,b in m['owns'])+' '+ ' '.join(t+': '+b+'.' for t,b in m['excludes'])+' Explicit compatibility: '+m['profile']+'. Limits: '+m['limit']))

    s=make_slide(m,'The executable surface','04 / Contract',
                 'These operations and implementation seams define the supported scope; versions and profiles remain explicit.')
    rows=m['operations']; rh=min(109,450//len(rows))
    table(s,['Operation / seam','Responsibility','Contract consequence'],rows,[400,535,521],row_h=rh,size=25)
    band(s,m['limit'],size=25)
    note(s,source_note(m,'Walk the contract from inputs to effects. '+ ' '.join(a+': '+b+'; '+c+'.' for a,b,c in rows)+' Operation groups on this slide are not a new coverage denominator. The evidence ledger distinguishes new operations from inherited dependencies. Supporting internal helpers are labelled as seams and are not advertised remote services.'))

    s=make_slide(m,'A worked example through the boundary','05 / Concrete behavior',m['example_label'])
    for i,(title,body) in enumerate(m['example']):
        x=72+i*370
        s.box(x,264,346,324,title,body,color,'white',tag=f'{i+1:02d} · STEP',title_size=31,body_size=28)
        if i<3:s.line(x+346,425,x+370,425,C[color],arrow=True)
    s.box(72,638,1456,112,'What the example establishes',m['takeaway'],color,'mint' if color=='teal' else 'ice',title_size=28,body_size=27)
    note(s,source_note(m,'Use this example to connect the responsibility to observable behavior. '+ ' '.join(f'{i+1}. {a}: {b}' for i,(a,b) in enumerate(m['example']))+' Evidence classification: '+m['example_label']+'. Do not infer performance, broad production readiness or extra runtime integrations from this example.'))

    s=make_slide(m,'Four invariants to preserve','06 / Behavioral guarantees',
                 'Each statement is bounded by the selected profile, authority model and tested failure model.')
    for i,(title,body) in enumerate(m['invariants']):
        x=72+(i%2)*744;y=245+(i//2)*243
        s.box(x,y,712,213,title,body,color,'white',tag=f'I{i+1}',title_size=30,body_size=27)
    note(s,source_note(m,'These invariants should survive provider substitution and future optimization. '+ ' '.join(a+': '+b for a,b in m['invariants'])+' The supporting tests and runtime evidence are in the linked sources; this slide does not claim a formal proof or a production security audit.'))

    s=make_slide(m,'Failure is part of the interface','07 / Recovery and refusal',
                 'A lost response, a missing prerequisite and a deliberate refusal require different interpretations.')
    table(s,['Boundary / trigger','Owner-authoritative outcome','Evidence / limitation'],m['recovery'],[455,585,416],row_h=145,size=25)
    band(s,'Recovery evidence covers same-host process termination with intact files; it does not prove power-loss durability.',size=24)
    note(s,source_note(m,'State the owner boundary before the recovery claim. '+ ' '.join(a+': '+b+' '+c+'.' for a,b,c in m['recovery'])+' A fixture can position the failure while a real process is killed. Local replay semantics do not imply exactly-once physical execution, a distributed transaction, or global failover. For pure/static modules the relevant failure is selection/refusal, not invented journal recovery.'))

    s=make_slide(m,'Measurements and benchmark gaps','08 / Benchmarks',
                 'Observed values, contract limits and proposed experiments are explicitly different kinds of evidence.')
    for i,(value,label,context) in enumerate(m['metrics']):
        x=72+i*496
        s.rect(x,244,464,263,C['white'],C[color],13)
        fit_text(s,x+23,265,418,value,60,C[color])
        s.text(x+23,356,418,label,26,C['ink'],'bold')
        s.text(x+23,431,418,context,22,C['muted'])
    s.text(76,537,1444,m['measurement'],25,C['muted'])
    s.box(72,665,1456,151,'PROPOSED BENCHMARK · NOT RUN',m['benchmark'], 'amber','sand',title_size=24,body_size=24)
    note(s,source_note(m,'Read every number with its unit and source class. '+ ' '.join(v+' '+label+': '+context+'.' for v,label,context in m['metrics'])+' '+m['measurement']+' '+m['benchmark']+' No new benchmark is executed for this presentation. Do not compare overlapping suite times or use a one-run workflow measurement as a latency percentile.'))

    s=make_slide(m,'Current state: what is real, what is not','09 / Evidence classification',
                 'Current supported regressions pass; historical observations and unsatisfied capabilities keep their labels.')
    table(s,['Classification','Module-specific state'],[
        ('REAL / IMPLEMENTED',m['real']),('FIXTURE / LOCAL TEST POLICY',m['fixture']),
        ('BLOCKED / UNSUPPORTED',m['blocked']),('UNRUN',m['unrun'])],[380,1076],row_h=112,size=25)
    band(s,'M5 final tested runtime: bfb0ec8 · evidence: 3dc6c11 · module representation is not product completeness.',size=24)
    note(s,source_note(m,'Implemented local code is not automatically a production provider. Real: '+m['real']+' Fixture: '+m['fixture']+' Blocked or unsupported: '+m['blocked']+' Unrun: '+m['unrun']+' All required M5 gates passed in the recorded final run, including legacy M1–M4 behavior; this presentation does not rerun those integrations. Human maintainers remain unassigned.'))

    s=make_slide(m,'Future directions need acceptance criteria','10 / Proposed work · not implemented',
                 'These are discussion options, not a committed roadmap or permission to expand the current profile.')
    table(s,['Direction','Prerequisite / design gate','Measure of success'],m['future'],[410,540,506],row_h=144,size=25)
    band(s,'Keep ownership, current authorization and explicit compatibility intact; qualify new semantics with a new profile.',size=24)
    note(s,source_note(m,'Discuss future work as conditional engineering proposals. '+ ' '.join(a+' requires '+b+'; success means '+c+'.' for a,b,c in m['future'])+' No new cognition, scheduler, migration or chain capability is implemented by this series. Any changed numerical semantics, placement or replay lifetime requires separate design and verification rather than a presentation claim.'))

    s=make_slide(m,'Evidence you can inspect and reproduce','11 / Sources and takeaway',
                 'Read the exact code, contracts and recorded run before treating a claim as a guarantee.')
    s.box(72,234,1456,112,'Takeaway',m['takeaway'],color,'mint' if color=='teal' else 'ice',title_size=28,body_size=28)
    s.text(80,370,1440,'SUPPORTED REPRODUCTION ENTRYPOINT · PREREQUISITES REQUIRED',18,C['muted'],'bold')
    s.text(80,410,1435,m['command'],24,C['ink'],'mono')
    s.text(80,489,1430,m['reproduction'],25,C['muted'])
    for i,path in enumerate(m['sources'][:4]):
        s.text(80,619+i*33,1435,path,21,C['blue'],'mono')
    s.text(80,770,1430,'Source '+catalogue.SOURCE_COMMIT+' · all citations and full notes accompany this deck.',19,C['muted'])
    note(s,source_note(m,'Conclude with: '+m['takeaway']+' The reproduction entrypoint is '+m['command']+'. '+m['reproduction']+' Build/export checks for this series are separate from runtime tests. Exact upstream pins remain in integration/hive/sources.json, integration/pln/sources.json, integration/pln/deduction-sources.json and the M4/M5 source manifests. Commands use fresh output/state; raw provider environments, credentials, journals and private IDs should not be published.'))
    assert len(base.SLIDES)==12
    return list(base.SLIDES)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--module',choices=[m['id'] for m in catalogue.MODULES])
    args=parser.parse_args()
    selected=[m for m in catalogue.MODULES if not args.module or m['id']==args.module]
    manifests=[]
    for m in selected:
        paths=[ROOT/p for p in m['sources']]
        assert all(p.exists() for p in paths),m['id']
        slides=build_module(m)
        manifest=render.export(m,slides,HERE/m['id'],QA/m['id'],paths)
        manifests.append(manifest)
        print(m['id'],len(slides),'slides',flush=True)
    if not args.module:
        combined=render.fitz.open();toc=[]
        for m in catalogue.MODULES:
            pdf=render.fitz.open(HERE/m['id']/'slides.pdf')
            first=len(combined)+1;toc.append([1,m['name'],first])
            combined.insert_pdf(pdf)
            manifest=json.loads((HERE/m['id']/'build-manifest.json').read_text())
            toc.extend([2,s['title'],first+s['slide']-1] for s in manifest['slides_manifest'])
        combined.set_toc(toc)
        combined.set_metadata({'title':'Omega × ASI — Fifteen module talks','author':'Omega × ASI module-interface project'})
        combined.save(HERE/'all-modules.pdf',garbage=4,deflate=True)
        ledger={'schema':'fusion-module-talks/1','source':catalogue.SOURCE_COMMIT,'tested_runtime':catalogue.TESTED_COMMIT,
                'evidence':catalogue.EVIDENCE_COMMIT,'decks':15,'slides_per_deck':12,'total_slides':180,
                'benchmark_policy':'No new performance measurements; existing observations and contract bounds labelled separately from proposed benchmarks.',
                'module_names':[m['name'] for m in catalogue.MODULES],
                'input_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted({ROOT/p for m in catalogue.MODULES for p in m['sources']})}}
        (HERE/'series-manifest.json').write_text(json.dumps(ledger,indent=2)+'\n')
        # Source is kept beside generated outputs; all fifteen decks remain editable.
        with zipfile.ZipFile(HERE/'module-decks.zip','w',zipfile.ZIP_DEFLATED) as bundle:
            for m in catalogue.MODULES:
                for name in ['slides.pdf','slides.pptx','speaker-notes.md']:
                    bundle.write(HERE/m['id']/name,m['id']+'/'+name)
            bundle.write(HERE/'all-modules.pdf','all-modules.pdf')
            for name in ['catalogue.py','build_modules.py','render.py','check_modules.py','series-manifest.json']:
                bundle.write(HERE/name,'source/'+name)
            readme=['# Omega × ASI — fifteen module talks', '', '15 standalone talks; 12 editable slides each. Start with all-modules.pdf or choose a module below.', '', 'Every deck includes responsibility, scope, dependencies, why it matters, measurements/benchmark gaps, invariants, current state and proposed future directions.', '', 'No new performance or integration tests were executed for this presentation series. Existing observations and contract bounds are labelled separately from proposed experiments.', '', '| Module | PDF | PowerPoint | Notes |', '|---|---|---|---|']
            for item in catalogue.MODULES:
                d=item['id'];readme.append(f"| {item['name']} | [PDF]({d}/slides.pdf) | [PowerPoint]({d}/slides.pptx) | [Notes]({d}/speaker-notes.md) |")
            readme += ['', '[All talks](all-modules.pdf). Install [DejaVu fonts](fonts/) for faithful editing; [license](fonts/LICENSE.txt).', '', 'Source snippets in source/ are editorial references. Rebuild in the fusion-module-interfaces repository, which supplies shared renderer primitives, fonts and evidence inputs.', '', 'Source snapshot: '+catalogue.SOURCE_COMMIT+'. Tested runtime: '+catalogue.TESTED_COMMIT+'.', '', 'Speaker-note citations link directly to that immutable repository snapshot.']
            bundle.writestr('README.md','\n'.join(readme)+'\n')
            for font in sorted((HERE.parent/'fonts').iterdir()):
                if font.is_file():bundle.write(font,'fonts/'+font.name)
        print('15 decks / 180 slides; combined PDF and editable-deck bundle generated.')

if __name__=='__main__':main()
