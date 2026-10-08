import json
import sqlite3
import tempfile
from pathlib import Path

import tracker_worker


def test_rotates_candidates_until_success():
    with tempfile.TemporaryDirectory() as directory:
        db_path = Path(directory) / 'jobs.sqlite'
        db = sqlite3.connect(db_path)
        db.execute('CREATE TABLE jobs (id TEXT, container TEXT, carrier TEXT, carrier_name TEXT, candidates TEXT, status TEXT, payload TEXT, error TEXT)')
        db.execute('INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?, ?)', ('job', 'TEST1234567', 'maersk', '自动轮询承运商', json.dumps(['maersk', 'msc']), 'queued', None, None))
        db.commit(); db.close()
        calls = []
        original = tracker_worker.subprocess.run

        def fake_run(command, **_):
            calls.append(command[-1])
            payload = {'ok': command[-1] == 'msc', 'result': {'carrier': 'MSC', 'events': []}}
            return type('Done', (), {'stdout': 'TRACKER_JSON=' + json.dumps(payload), 'stderr': ''})()

        tracker_worker.subprocess.run = fake_run
        try:
            tracker_worker.main(str(db_path), 'job')
        finally:
            tracker_worker.subprocess.run = original
        verify = sqlite3.connect(db_path)
        row = verify.execute('SELECT status, carrier_name FROM jobs WHERE id="job"').fetchone()
        verify.close()
        assert calls == ['maersk', 'msc'] and row == ('done', 'MSC')


if __name__ == '__main__':
    test_rotates_candidates_until_success()
    print('ok')
