"""Unchanged S06 test, with diagnostic status captured before temporary cleanup."""
import json
from pathlib import Path
import unittest
from integration.neoclaw.test_channel_loop import NativeChannel
original = NativeChannel.traffic_until

def capture(self, channel, count, run=None, process=None):
    try:
        return original(self, channel, count, run, process)
    except BaseException:
        status = None
        if run is not None:
            path = Path(run.app['status_file'])
            if path.exists():
                status = json.loads(path.read_text())
        Path('evidence/s07/baseline-native-failure-status.json').write_text(json.dumps(dict(
            placement=channel.placement, status=status,
            process_returncode=process.poll() if process is not None else None), indent=2)+'\n')
        raise

NativeChannel.traffic_until = capture
suite = unittest.defaultTestLoader.loadTestsFromName('integration.neoclaw.test_channel_loop.NativeChannel.test_local_and_https_native_consumption_equal_text_burst_and_send')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
