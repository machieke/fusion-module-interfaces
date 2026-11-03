"""Closed read surface for fresh-authority Phase 3 restored service owners."""
import json
from pathlib import Path
from fusion.contracts import require

READS={
 '/preview/session':{'observe','list','capacity'},
 '/reference-cognition':{'get','getMany','availability','head','readCommits','capacity','observe',
     'readEpisode','readEvidence','pendingEvidence','readOccurrence','readBelief','observeDecision','readDecisions'},
 '/preview/facets':{'authorize','historySnapshot','readHistory','getRelation','outgoing','incoming','read','version'},
 '/preview/memory':{'head','activeSet','readEvents','disclose','published','current','ready','authorize'},
 '/preview/owner-state':{None},
 '/memory-source':{'get','head','readCommits','observe'},
 '/s03-read':{'getMany','authorize'},'/s03-append':{'get','observe','published','authorize'},
}


class ReadPorts:
    def __init__(self,run,role):self.run,self.role=Path(run),role
    def invoke(self,path,credential,q):
        require(type(q) is dict and path in READS and q.get('operation') in READS[path],'UNAUTHORIZED')
        if path=='/preview/session':
            require(self.role in ('omega-agent','omega-agent-b'),'UNAUTHORIZED')
            from fusion.sustained_restore import Ports
            return Ports(self.run/'owner.json').invoke(credential,q)
        if path=='/preview/facets' and q['operation']=='authorize':
            require(q.get('args',[None])[0] in ('historySnapshot','readHistory','getRelation','outgoing','incoming','read','version'),'UNAUTHORIZED')
        cfg=json.loads((self.run/'owner.json').read_bytes())
        from .sustained_private import ScopeRouter
        router=ScopeRouter(self.run/'owner.json',self.role)
        if 'scope_routes' in cfg and router.matches(q):
            # Restore never builds Search's initial view or loads E5/model.
            if self.role=='fusion-search' and path in ('/s03-append','/s03-read'):
                from fusion.memory_services import SearchPorts
                selected=router.selection(q['scope'])
                router.search[q['scope']]=SearchPorts(Path(selected['directory'])/'owner.json')
            return router.invoke(path,credential,q)
        if path=='/reference-cognition':
            from fusion.cognitive_services import Ports
            return Ports(self.run/'cognitive-owner.json',self.role).invoke(path,credential,q)
        if path=='/preview/facets':
            from fusion.preview_ports import Ports
            return Ports(self.run/'facet-owner.json',self.role).invoke(credential,q)
        if path=='/preview/memory':
            from fusion.preview_memory_services import Ports
            return Ports(self.run/'owner.json',self.role).invoke(credential,q)
        if path=='/preview/owner-state':
            require(self.role=='fusion-attention','UNAUTHORIZED')
            from fusion.sustained_observation import invoke
            return invoke(self.run/'cognitive-owner.json',credential,q)
        from fusion.memory_services import StoragePorts,SearchPorts
        require(self.role in ('fusion-storage','fusion-search'),'UNAUTHORIZED')
        owner=StoragePorts(self.run/'owner.json') if self.role=='fusion-storage' else SearchPorts(self.run/'owner.json')
        return owner.invoke(path,credential,q)
