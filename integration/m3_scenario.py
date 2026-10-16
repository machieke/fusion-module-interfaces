"""Fixed generated episode and two grounded tasks; no runtime-selected private input."""
from fusion import cognition_contracts as c
from fusion import memory_contracts as m
from fusion.contracts import canonical, digest, require
from fusion.ports import Mutation, EvidenceSubmission, Stimulus, WorkBudget, InferenceRequest
from fusion.responses import envelope


def run_generated(modules,scope,identity,seed,prefer,deadline_ms):
    atoms,episodes,beliefs=modules.atoms,modules.episodes,modules.beliefs
    intent=canonical({'scenario':'generated-private-m3','seed':seed,'prefer':prefer,'deadline_ms':deadline_ms})
    atoms.create(Mutation(scope,'intent/'+identity),'application/fusion-intent',intent)
    context='inference/'+identity
    episode=episodes.recordEpisode(Mutation(scope,'episode/'+identity),'sensor-a')['ref']
    entries=[];all_roles=[]
    for index,name in enumerate(('a','b')):
        roles={}
        def create(key,kind,record):
            return atoms.create(Mutation(scope,digest(canonical([identity,name,key]))),kind,canonical(record))['ref']
        for role in ('p','q','r'):
            roles[role]=create(role,'application/fusion-claim',{'predicate':'pln:proposition','arguments':[f'generated-{seed}-{name}-{role}'],'positive':True})
        for role,left,right in [('pq','p','q'),('qr','q','r'),('pr','p','r')]:
            roles[role]=create(role,'application/fusion-claim',{'predicate':'pln:implication',
                'arguments':[digest(canonical(roles[left])),digest(canonical(roles[right]))],'positive':True})
        task=create('task','application/fusion-task',{'profile':c.RULE,'context':context,'roles':roles})
        vector=[]
        for n,role in enumerate(c.ROLES[:5]):
            occurrence=digest(canonical([identity,name,role]))
            payload=create('payload-'+role,'application/fusion-generated',{'text':f'PRIVATE-M3-{seed}-{name}-{role}','assessment':'explicit generated fixture'})
            truth={'model':c.MODEL,'strength':'0.5' if n<3 else '0.8','confidence':'0.8' if n<3 else '0.7','evidence_count':None}
            event={'occurrence_id':occurrence,'kind':'observation','source':'sensor-a','observed_time':'2026-10-16T00:00:00Z',
                'payload':payload,'causation':[],'provenance':[],'numerical':{'claim':roles[role],'context':context,
                'relationship':'supports','truth':truth,'ingestion_profile':m.INGESTION}}
            receipt=episodes.appendEvent(Mutation(scope,'append/'+occurrence),episode,index*5+n,event)
            initial=beliefs.readBelief(roles[role],context,0)
            decision=beliefs.submitEvidence(EvidenceSubmission(Mutation(scope,'observe/'+occurrence),roles[role],context,
                receipt['evidence'],None,0,c.BELIEF_PROFILE,initial['runtime_selection']))
            c.response(c.decision,decision,roles[role],context,initial['runtime_selection'])
            vector.append({'claim':roles[role],'context':context,'revision':1,'support_id':decision['support_id']})
        entries.append({'task':task,'premises':vector});all_roles.append(roles)
        cause=digest(canonical([identity,name,'ingress']))
        modules.attention.submitStimulus(Stimulus(Mutation(scope,'stimulus/'+cause),context,task,'20' if prefer==name else '10',
            cause,0,modules.attention.profile()['policy'],0,'ingress'))
    workset=atoms.create(Mutation(scope,'workset/'+identity),'application/fusion-workset',
        canonical({'profile':c.WORKSET,'context':context,'tasks':entries}))['ref']
    def event(kind,n,detail):
        occurrence=digest(canonical([identity,kind]));payload=atoms.create(Mutation(scope,'payload/'+occurrence),
            'application/fusion-inference-trace',canonical(detail))['ref']
        return episodes.appendEvent(Mutation(scope,'trace/'+occurrence),episode,n,{'occurrence_id':occurrence,'kind':kind,
            'source':'sensor-a','observed_time':'2026-10-16T00:00:00Z','payload':payload,'causation':[workset],
            'provenance':[],'numerical':None})
    event('action',10,{'workset':workset,'rule':c.RULE,'budget':1})
    request=InferenceRequest(Mutation(scope,'inference/'+identity),context,workset,modules.selections,WorkBudget(2,1,3,deadline_ms))
    result=modules.controller.step(request)
    if result['status']=='complete':event('result',11,result)
    return {'episode':episode,'entries':entries,'roles':all_roles,'context':context,'workset':workset,'request':request,'result':result}
