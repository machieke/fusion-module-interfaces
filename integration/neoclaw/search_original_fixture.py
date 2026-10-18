"""Original native search oracle: explicitly recorded SDK .text responses."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, os.environ['NEOCLAW_SEARCH_ORIGINAL_SITE'])
sys.path.insert(0, os.environ['NEOCLAW_SEARCH_ORIGINAL_HELPER'])
from ddgs.ddgs import DDGS
import websearch


class RecordedDDGS(DDGS):
    def text(self, query, max_results=10):
        entry = json.loads(Path(os.environ['NEOCLAW_SEARCH_ORIGINAL_RECORDING']).read_text())['observations'][0]
        if 'error' in entry: raise RuntimeError('RECORDED_FAILURE')
        return entry['rows']


websearch.DDGS = RecordedDDGS
