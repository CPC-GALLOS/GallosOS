"""Destructive guest-only acceptance probe, injected into a disposable QEMU image.

Never run on a development host: this replaces /etc/gallos/gallos.toml and
requests contestant-session resets. The harness must supply the QEMU fixture.
"""

import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

POLICY = Path('/etc/gallos/gallos.toml')


def run(*args, **kwargs):
    result = subprocess.run(args, text=True, capture_output=True, **kwargs)
    if result.returncode:
        raise RuntimeError(f"{args}: {result.stdout} {result.stderr}")
    return result.stdout


def status():
    return json.loads(run('/usr/bin/gallosctl', 'status'))


def wait_mode(mode):
    for _ in range(90):
        state = status()
        if state['transition_status'] == 'error':
            raise AssertionError(state)
        if state['mode'] == mode and state['transition_status'] == 'ready':
            return state
        time.sleep(1)
    raise AssertionError(f'timeout waiting for {mode}: {state}')


def write_policy(start, end, expiration, wallpaper='default'):
    POLICY.parent.mkdir(mode=0o700, exist_ok=True)
    POLICY.write_text(
        '[global]\ntimezone="UTC"\n'
        f'config_expiration="{expiration.isoformat(timespec='seconds')}"\n'
        '[default]\nallowed_websites=["*"]\n'
        '[contest]\nallowed_websites=["10.0.2.2"]\n'
        f'wallpaper={json.dumps(wallpaper)}\n'
        f'[[contest.schedule]]\nstart="{start.isoformat(timespec='seconds')}"\nend="{end.isoformat(timespec='seconds')}"\n'
    )
    run('/usr/bin/gallosctl', 'reload')


def main():
    if os.environ.get("GALLOS_DISPOSABLE_GUEST_PROBE") != "1":
        raise RuntimeError("Probe requires the disposable guest fixture")
    for _ in range(90):
        if Path('/run/gallos/daemon.sock').exists():
            break
        time.sleep(1)
    wait_mode('Default')
    rules = run('nft', 'list', 'ruleset')
    assert '853' not in rules and 'telemetry_dns_blacklist' not in rules
    print('DRIFT-PASS neutral-network', flush=True)
    run('/usr/bin/python3', '-c', 'import sys,tomllib; assert sys.version_info >= (3,11); assert sys.implementation.name=="cpython"')
    run('/usr/local/bin/pypy3', '-c', 'import sys; assert sys.version_info[:3]==(3,9,18); assert sys.pypy_version_info[:3]==(7,3,15)')
    print('DRIFT-PASS python-separation', flush=True)
    now = datetime.now(timezone.utc)
    start, end = now-timedelta(minutes=1), now+timedelta(minutes=5)
    write_policy(start, end, now+timedelta(minutes=10))
    wait_mode('Contest')
    rules = run('nft', 'list', 'ruleset')
    assert 'policy drop' in rules
    assert 'dport 53' not in rules and 'dport 123' not in rules
    assert '192.168.50.1' not in rules and '192.168.1.1' not in rules
    print('DRIFT-PASS explicit-services', flush=True)
    child = subprocess.Popen(['sleep', '600'], user='contestant', group='contestant')
    write_policy(start, end, datetime.now(timezone.utc)+timedelta(seconds=2), '/missing-wallpaper.png')
    wait_mode('Contest')
    time.sleep(4)
    assert child.poll() is None, 'reload killed contestant process'
    assert status()['mode'] == 'Contest', 'expiry interrupted Contest'
    published = json.loads(Path('/run/gallos/wallpaper.json').read_text())
    assert published['path'].endswith('/contest.png')
    print('DRIFT-PASS hot-reload-expiry-wallpaper-fallback', flush=True)
    POLICY.write_text('[global]\ntimezone="UTC"\n[[contest.schedule]]\nstart="2026-01-01T00:00:00Z"\nend="2026-99-99T00:00:00Z"\n')
    invalid = subprocess.run(['/usr/bin/gallosctl', 'reload'], capture_output=True)
    assert invalid.returncode != 0 and child.poll() is None, (invalid.returncode, invalid.stdout, invalid.stderr, child.poll(), status())
    assert status()['mode'] == 'Contest'
    print('DRIFT-PASS invalid-reload', flush=True)
    write_policy(start, end, now-timedelta(seconds=1))
    wait_mode('Contest')
    run('systemctl', 'restart', 'gallosd')
    time.sleep(3)
    wait_mode('Contest')
    print('DRIFT-PASS restart-deadline', flush=True)
    write_policy(start, datetime.now(timezone.utc)-timedelta(seconds=1), now-timedelta(seconds=1))
    wait_mode('Default')
    print('DRIFT-PASS changed-end', flush=True)
    override = Path('/etc/systemd/system/gallos-usb-storage@lock.service.d')
    override.mkdir(parents=True, exist_ok=True)
    (override / 'acceptance.conf').write_text('[Service]\nExecStart=\nExecStart=/usr/bin/false\n')
    run('systemctl', 'daemon-reload')
    run('/usr/bin/gallosctl', 'contest', 'start', '1')
    for _ in range(30):
        if status()['transition_status'] == 'error':
            break
        time.sleep(1)
    assert status()['transition_status'] == 'error'
    assert not Path('/run/gallos/kiosk-ready').exists()
    print('DRIFT-PASS failure-gate', flush=True)
    (override / 'acceptance.conf').unlink()
    run('systemctl', 'daemon-reload')
    run('/usr/bin/gallosctl', 'contest', 'start', '1')
    wait_mode('Contest')
    print('DRIFT-PASS manual-recovery', flush=True)
    run('/usr/bin/gallosctl', 'contest', 'stop')
    wait_mode('Default')
    run('/usr/bin/gallosctl', 'contest', 'stop')
    time.sleep(2)
    record = Path('/run/gallos/transition.json')
    assert json.loads(record.read_text())['clock']['manual_mode'] == 'Default'
    run('systemctl', 'restart', 'gallosd')
    time.sleep(3)
    wait_mode('Default')
    assert json.loads(record.read_text())['clock']['manual_mode'] == 'Default'
    print('DRIFT-PASS F02-same-mode-stop-restart', flush=True)
    POLICY.write_text('[global]\ntimezone="UTC"\n[default]\nallowed_websites=["*"]\n[contest]\nallowed_websites=["10.0.2.2"]\nduration_minutes=300\n')
    run('/usr/bin/gallosctl', 'reload')
    wait_mode('Default')
    run('/usr/bin/gallosctl', 'contest', 'start', '60')
    wait_mode('Contest')
    run('/usr/bin/gallosctl', 'contest', 'start', '61')
    time.sleep(2)
    before = json.loads(record.read_text())['clock']
    assert before['manual_duration'] == 3660, before
    child = subprocess.Popen(['sleep', '600'], user='contestant', group='contestant')
    run('/usr/bin/gallosctl', 'reload')
    wait_mode('Contest')
    after = json.loads(record.read_text())['clock']
    assert after['manual_duration'] == 3660, after
    assert after['manual_origin'] == before['manual_origin'], (before, after)
    assert child.poll() is None
    print('DRIFT-PASS F01-unchanged-duration', flush=True)
    import shutil
    shutil.copyfile('/usr/share/backgrounds/gallos/contest.png', '/usr/libexec/custom.png')
    POLICY.write_text(POLICY.read_text() + 'wallpaper="custom.png"\n')
    run('/usr/bin/gallosctl', 'reload')
    wait_mode('Contest')
    published = json.loads(Path('/run/gallos/wallpaper.json').read_text())
    assert published['path'] == '/usr/libexec/custom.png', published
    print('DRIFT-PASS F04-absolute-wallpaper-publication', flush=True)
    run('systemctl', 'restart', 'gallosd')
    time.sleep(3)
    wait_mode('Contest')
    restored = json.loads(record.read_text())['clock']
    assert restored['manual_duration'] == 3660
    assert restored['manual_origin'] == before['manual_origin']
    print('DRIFT-PASS F02-same-mode-start-restart', flush=True)
    record.unlink()
    record.mkdir()
    run('/usr/bin/gallosctl', 'reload')
    for _ in range(30):
        if status()['transition_status'] == 'error':
            break
        time.sleep(1)
    assert status()['transition_status'] == 'error', status()
    assert not Path('/run/gallos/kiosk-ready').exists()
    for _ in range(30):
        if subprocess.run(['pgrep', '-x', 'labwc'], capture_output=True).returncode != 0:
            break
        time.sleep(1)
    assert subprocess.run(['pgrep', '-x', 'labwc'], capture_output=True).returncode != 0
    print('DRIFT-PASS F03-journal-failure-contained', flush=True)
    record.rmdir()
    run('/usr/bin/gallosctl', 'contest', 'start', '60')
    wait_mode('Contest')
    print('DRIFT-PASS F03-journal-recovery', flush=True)
    # Full graphical acceptance remains separate if the compositor is absent.
    for _ in range(30):
        graphical = subprocess.run(['pgrep', '-a', 'labwc'], text=True, capture_output=True)
        wallpaper = subprocess.run(['pgrep', '-a', 'swaybg'], text=True, capture_output=True)
        if graphical.returncode == 0 and wallpaper.returncode == 0:
            break
        time.sleep(1)
    assert graphical.returncode == 0 and wallpaper.returncode == 0, 'graphical wallpaper session missing'
    print('DRIFT-GRAPHICS', graphical.stdout.strip(), wallpaper.stdout.strip(), flush=True)
    print('DRIFT-ALL-PASS', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        print('DRIFT-FAIL', flush=True)
        subprocess.run(['journalctl', '-u', 'gallosd', '-n', '60', '--no-pager'])
        raise
