"""One short-lived tracking worker launched by PHP."""
import json
import sqlite3
import subprocess
import sys
import time
import traceback
from pathlib import Path


def update(db, job_id, status, payload=None, error=None):
    db.execute('UPDATE jobs SET status=?, payload=?, error=? WHERE id=?',
               (status, json.dumps(payload, ensure_ascii=False) if payload else None, error, job_id))
    db.commit()


def log_failure(container, carrier, started, error, stderr):
    directory = Path(__file__).with_name('data') / 'logs'
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / 'tracker.log'
    if log.exists() and log.stat().st_size > 1048576:
        log.replace(log.with_suffix('.log.1'))
    detail = stderr.strip().replace('\n', ' ')[:1000]
    log.open('a', encoding='utf-8').write(
        f'{time.strftime("%Y-%m-%dT%H:%M:%S")} carrier={carrier} container={container} '
        f'elapsed={time.monotonic() - started:.1f}s error={error} stderr={detail}\n'
    )


def run_group(container, carriers, timeout):
    """Run a carrier group concurrently and return its first valid payload."""
    env = {**__import__('os').environ, 'TRACKER_TIMEOUT_SECONDS': '22',
           'TRACKER_HEADLESS': '1' if sys.platform != 'win32' else '0'}
    processes = {
        carrier: subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name('tracker_cli.py')), container, carrier],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', env=env,
        ) for carrier in carriers
    }
    deadline = time.monotonic() + timeout
    failures, stderr = [], ''
    try:
        while processes and time.monotonic() < deadline:
            for carrier, process in list(processes.items()):
                if process.poll() is None:
                    continue
                stdout, error = process.communicate()
                del processes[carrier]
                stderr += error
                line = next((line[13:] for line in stdout.splitlines() if line.startswith('TRACKER_JSON=')), '')
                payload = json.loads(line) if line else {'ok': False}
                if payload.get('ok'):
                    return payload['result'], failures, stderr
                failures.append(carrier)
            time.sleep(.1)
        failures.extend(processes)
        return None, failures, stderr
    finally:
        for process in processes.values():
            process.terminate()
        for process in processes.values():
            try:
                process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()


def main(db_path, job_id):
    db = sqlite3.connect(db_path)
    row = None
    started = time.monotonic()
    stderr = ''
    try:
        row = db.execute('SELECT container, carrier, candidates FROM jobs WHERE id=?', (job_id,)).fetchone()
        if not row:
            return
        update(db, job_id, 'running')
        candidates = json.loads(row[2]) if row[2] else [row[1]]
        failures = []
        groups = [[carrier for carrier in candidates if carrier != '17track']]
        if '17track' in candidates:
            groups.append(['17track'])
        for carriers in groups:
            if not carriers or time.monotonic() - started > 55:
                continue
            payload, failed, output = run_group(row[0], carriers, min(25, 55 - (time.monotonic() - started)))
            stderr += output
            failures.extend(failed)
            if payload:
                db.execute('UPDATE jobs SET carrier_name=? WHERE id=?', (payload.get('carrier', carriers[0]), job_id))
                db.commit()
                update(db, job_id, 'done', payload)
                return
        raise RuntimeError('未找到可查询结果：' + ', '.join(failures))
    except Exception as exc:
        if row:
            update(db, job_id, 'error', error=str(exc))
            log_failure(row[0], row[1], started, traceback.format_exc().splitlines()[-1], stderr)
    finally:
        db.close()


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
