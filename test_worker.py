import json
import sqlite3
import tempfile
from pathlib import Path

import tracker_worker


def test_queries_carriers_together_then_falls_back():
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / 'jobs.sqlite'
        db = sqlite3.connect(db_path)
        db.execute('CREATE TABLE jobs (id TEXT, container TEXT, carrier TEXT, carrier_name TEXT, candidates TEXT, status TEXT, payload TEXT, error TEXT)')
        db.execute('INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)', ('job', 'TEST1234567', 'maersk', '自动轮询承运商', json.dumps(['maersk', 'msc', '17track']), 'queued', None, None))
        db.commit(); db.close()
        calls = []
        original = tracker_worker.subprocess.Popen

        class FakeProcess:
            def __init__(self, command, **_):
                calls.append(command[-1])
                self.carrier = command[-1]

            def poll(self):
                return 0

            def communicate(self, **_):
                payload = {'ok': self.carrier == 'msc', 'result': {'carrier': 'MSC', 'events': []}}
                return 'TRACKER_JSON=' + json.dumps(payload), ''

            def terminate(self):
                pass

            def kill(self):
                pass

        def fake_popen(command, **kwargs):
            return FakeProcess(command, **kwargs)

        tracker_worker.subprocess.Popen = fake_popen
        try:
            tracker_worker.main(str(db_path), 'job')
        finally:
            tracker_worker.subprocess.Popen = original
        verify = sqlite3.connect(db_path)
        row = verify.execute('SELECT status, carrier_name, payload FROM jobs WHERE id="job"').fetchone()
        verify.close()
        assert calls == ['maersk', 'msc'] and row[:2] == ('done', 'MSC') and json.loads(row[2])['_source'] == 'msc'


if __name__ == '__main__':
    test_queries_carriers_together_then_falls_back()
    print('ok')
