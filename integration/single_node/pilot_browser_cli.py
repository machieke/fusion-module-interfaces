"""Private loopback browser gateway, provisioned without Kubernetes credentials.

A trusted operator can expose the private ClusterIP application ports using an
existing private tunnel/port-forward. The gateway receives only its provisioned
scope credentials and never calls kubectl or reads a kubeconfig.
"""
import argparse
import signal
import threading
from http.server import ThreadingHTTPServer
from fusion.contracts import require
from .pilot_browser_sessions import Sessions
from .pilot_workbench import ScopedWorkbench
from .preview_workbench import handler


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',required=True)
    parser.add_argument('--port',type=int,default=8878)
    parser.add_argument('--listen',choices=('127.0.0.1','0.0.0.0'),default='127.0.0.1',
                        help='ClusterIP pod listener still requires the explicit loopback port-forward access path')
    args=parser.parse_args();require(1024<=args.port<=65535)
    workbench=ScopedWorkbench(args.configuration);sessions=Sessions(args.configuration)
    server=ThreadingHTTPServer((args.listen,args.port),handler(workbench,args.port,sessions))
    server.daemon_threads=True
    def stop(*_):threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop)
    print('Omega scoped pilot browser: http://127.0.0.1:'+str(args.port),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
