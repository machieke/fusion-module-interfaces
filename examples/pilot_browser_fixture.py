"""Generation-disabled UI qualification fixture, never a native workflow pass.

Uses the real fresh application SQLite owner, descriptors and browser handler.
Its upstream transport is the test fixture adapter and no native tool/model is
launched. It exists only to drive browser rendering/security before deployment.
"""
import argparse
from http.server import ThreadingHTTPServer
from fusion.contracts import canonical
from integration.single_node.preview_workbench import handler
from tests.test_pilot_browser import BrowserTests


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8878);args=parser.parse_args()
    fixture=BrowserTests();fixture.setUp();fixture.close()
    for user in fixture.browser_cfg['users'].values():user['session_seconds']=600
    fixture.browser_path.write_bytes(canonical(fixture.browser_cfg))
    fixture.cfg['native_sessions']['pilot_subscriptions']='application-commit-subscription/1'
    fixture.path.write_bytes(canonical(fixture.cfg));fixture.allocate('visual-fixture-session')
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(fixture.workbench,args.port,fixture.sessions))
    print('UI FIXTURE: real owner receipts; native tools and model NOT_RUN. http://127.0.0.1:'+str(args.port),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();fixture.doCleanups()


if __name__=='__main__':main()
