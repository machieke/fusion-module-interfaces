import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest

from fusion.contracts import ContractError
from fusion.preview_workspace import Workspace


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.revoked = False

    def auth(self, who, scope, op):
        if who != 'A' or scope != 'synthetic-files' or self.revoked: raise ContractError('UNAUTHORIZED')

    def open(self, **kwargs):
        return Workspace(self.root/'files', self.root/'owner.sqlite', self.auth, scope='synthetic-files', **kwargs)

    def test_native_content_atomic_revision_and_lost_reply_replay(self):
        owner = self.open()
        try:
            one = owner.mutate('A', 'synthetic-files', 'one', 'write', 'note.txt', 'hello', 0)
            two = owner.mutate('A', 'synthetic-files', 'two', 'append', 'note.txt', ' world', 1)
            self.assertEqual(owner.mutate('A', 'synthetic-files', 'two', 'append', 'note.txt', ' world', 1), two)
            self.assertEqual(owner.read('A', 'synthetic-files', 'note.txt')['text'], 'hello world\n')
            self.assertEqual(one['revision'], 1)
            with self.assertRaisesRegex(ContractError, 'CONFLICT'):
                owner.mutate('A', 'synthetic-files', 'three', 'write', 'note.txt', 'stale', 1)
            self.revoked = True
            with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'):
                owner.mutate('A', 'synthetic-files', 'two', 'append', 'note.txt', ' world', 1)
        finally: owner.close()

    def test_path_links_special_files_and_foreign_scope(self):
        owner = self.open()
        try:
            for path in ('../escape', '/etc/passwd', 'a/b', '.hidden', 'file\x00'):
                with self.assertRaises(ContractError): owner.read('A', 'synthetic-files', path)
            target = self.root/'private'; target.write_text('secret')
            os.symlink(target, self.root/'files'/'symlink')
            os.link(target, self.root/'files'/'hardlink')
            os.mkfifo(self.root/'files'/'fifo')
            for name in ('symlink', 'hardlink', 'fifo'):
                with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): owner.read('A', 'synthetic-files', name)
            with self.assertRaisesRegex(ContractError, 'UNAUTHORIZED'): owner.read('A', 'synthetic-other', 'note')
        finally: owner.close()

    def test_real_process_kill_after_file_effect_recovers_without_reappend(self):
        owner = self.open()
        owner.mutate('A', 'synthetic-files', 'one', 'write', 'note', 'base', 0)
        owner.close()
        program = '''import os,signal,sys
from fusion.preview_workspace import Workspace
def stop(stage):
 if stage == 'after_workspace_effect': os.kill(os.getpid(),signal.SIGKILL)
w=Workspace(sys.argv[1],sys.argv[2],lambda *a:None,scope='synthetic-files',hook=stop)
w.mutate('A','synthetic-files','two','append','note','plus',1)
'''
        killed = subprocess.run([sys.executable, '-c', program, str(self.root/'files'), str(self.root/'owner.sqlite')])
        self.assertEqual(killed.returncode, -signal.SIGKILL)
        owner = self.open()
        try:
            result = owner.mutate('A', 'synthetic-files', 'two', 'append', 'note', 'plus', 1)
            self.assertEqual(result['revision'], 2)
            self.assertEqual(owner.read('A', 'synthetic-files', 'note')['text'], 'baseplus\n')
        finally: owner.close()


if __name__ == '__main__': unittest.main()
