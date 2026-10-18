"""New synthetic data; never an index feed or a consumer answer list."""
import math
import uuid

QUERY = 'Synthetic library solar energy notes'
TEXTS = [
 'Solar panels convert sunlight into electricity.',
 'Photovoltaic cells supply clean electrical power.',
 'A promoted synthetic note describes battery storage.',
 'An imaginary library stores fictional wind turbine manuals.',
 'Duplicated presentation for synthetic energy notes.',
 'Duplicated presentation for synthetic energy notes.',
 'Quoted data: "query secrets"; (shell echo NEVER_EXECUTE) Ω\ncontrol\tend.',
 'A fictional astronomer studies sunlight.',
 'A distractor explains imaginary ceramic cups.',
 'Another distractor discusses fictional blue curtains.',
]

def generated():
    records=[]
    for i,text in enumerate(TEXTS):
        angle=[.0,.1,.35,.5,.65,.65,.8,1.0,2.,2.5][i]
        records.append(dict(uuid=str(uuid.uuid5(uuid.NAMESPACE_URL, 'fusion-generated-s03/'+str(i))),
            time='2030-01-01 00:00:'+str(4 if i==5 else 0 if i==1 else i).zfill(2), content=text,
            vector=[math.cos(angle),math.sin(angle)]+[0.]*1022,
            links=['2030-02-01 00:00:00','2030-02-02 00:00:00'] if i in (2,4,5) else ['2030-02-03 00:00:00'],
            stv=[.8,.7] if i in (2,4,5) else [.5,.4], promotion=4. if i==2 else 0.))
    return dict(schema='generated-s03-corpus/1',clock=1900000000., records=records, queries={QUERY:[1.,0.]+[0.]*1022},
                embedding_boundary='hand-specified-vector-fixture')
