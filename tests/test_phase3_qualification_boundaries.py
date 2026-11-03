"""Runner dataflow with explicit operator API fixtures; no native pass claimed."""
import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from integration.single_node.sustained_qualification import Runner

class OperatorDataflow(unittest.TestCase):
 def test_cognition_uses_owning_session_write_and_never_foreign_local_receipt(self):
  with tempfile.TemporaryDirectory() as directory:
   r=Runner(SimpleNamespace(namespace='explicit-operator-fixture'),Path(directory)/'run');r.ids={'omega-agent':['closed-first','overlap-a'],'omega-agent-b':['closed-first-b','overlap-b']}
   r.report['first_memory']={'memory':{'handle':'earlier-session-handle'}}
   r.report['overlap']={'results':{'omega-agent':json.dumps({'memory':{'handle':'same-session-write'}})}}
   seen=[]
   def run(command,role='omega-agent',session=0):
    seen.append((command,role,session))
    if command.startswith('delegate '):return json.dumps(dict(deadline=1,task='captured-task'))
    if command.startswith('inspect-atom '):return json.dumps(dict(caller_acknowledged=True))
    if command=='episodes current':return json.dumps(dict(events=[dict(kind='external-observation',body={'source':{'handle':'native-event'}})]))
    if command.startswith('support'):return 'REVISION-SUCCESS'
    if command.startswith('contradict'):return 'retained-alternative'
    if command.startswith('query'):return '_apostrophe_stv_apostrophe_, 1.0, 0.5'
    return 'priority-result'
   r.run=run;r.call=lambda role,op,sid=None,*a:({'inputs':[dict(assignment='delegated-result',deadline=1,state='complete')]} if op=='observe' else [])
   r.handoffs({'omega-agent':1,'omega-agent-b':1})
   assessments=[row for row in seen if row[0].startswith(('support','contradict'))]
   self.assertEqual(len(assessments),3)
   self.assertTrue(all('same-session-write' in row[0] and row[2]==1 for row in assessments))
   self.assertFalse(any('earlier-session-handle' in command for command,_,_ in seen))
