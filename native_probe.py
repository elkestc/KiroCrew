"""Synthetic containment probe; never run a project test suite on a host.

The controller runs only on disposable GitHub-hosted runners. Test payloads run
in a mount-free Windows container or a default-deny macOS filesystem sandbox.
Only numeric status and hashes are emitted. No credentials are used or read.
"""

import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import uuid


def digest(data):
    return hashlib.sha256(data).hexdigest()


def execute(argv, **kwargs):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=kwargs.pop('timeout', 120), **kwargs)
    if result.returncode:
        known_errors = ['manifest unknown', 'no matching manifest', 'access is denied',
                        'failed to register layer', 'no space left', 'timeout',
                        'context deadline exceeded', 'hcsshim', 'cannot find',
                        'network', 'connection', 'not found', 'unexpected status',
                        'unauthorized', 'tls', 'certificate', 'mismatch',
                        'directory', 'exist', 'invalid', 'not supported',
                        'copying between containers', 'no such', 'externally managed',
                        'externally-managed', 'virtual environment', 'buildx', 'dockerfile',
                        'no builder', 'error during connect', 'hyper-v', 'compute system',
                        'no solution', 'no build', '--system', 'group', 'unknown',
                        'network adapter', 'invalid response', 'failed to create', 'pull access denied',
                        'docker_engine', 'working directory', 'failed to open', 'uv pip',
                        'error: failed to', 'isolation', 'the system cannot find the file specified']
        lowered = (result.stderr + result.stdout).decode('utf-8', errors='replace').lower()
        raise RuntimeError(json.dumps({'exit_code': result.returncode,
                                      'stderr_sha256': digest(result.stderr),
                                      'stdout_sha256': digest(result.stdout),
                                      'operation': Path(argv[0]).name + ':' + argv[1],
                                      'diagnostic_tags': [tag for tag in known_errors if tag in lowered]}))
    return result.stdout


def payload(request_file):
    # This entry point is invoked only after the controller verifies containment.
    sys.path.insert(0, str(Path(__file__).parent))
    from test_isolation import AllowedTestRoot, TestRootViolation

    request = json.loads(Path(request_file).read_text(encoding='utf-8'))
    root = Path(request['root'])
    root.mkdir(parents=True, exist_ok=True)
    fake_home = root / 'home'
    fake_home.mkdir(exist_ok=True)
    outer = root / 'synthetic-external'
    outer.mkdir()
    sentinel = outer / 'credentials'
    sentinel.write_bytes(b'FAKE_TEST_CREDENTIAL_NEVER_VALID\n')
    before = digest(sentinel.read_bytes())
    link = fake_home / '.aws'
    if os.name == 'nt':
        execute(['cmd.exe', '/d', '/c', 'mklink', '/J', str(link), str(outer)])
    else:
        link.symlink_to(outer, target_is_directory=True)
    boundary = AllowedTestRoot(str(fake_home))
    rejected = []
    for mode in ('rb', 'wb'):
        try:
            validated = boundary.validate(link / 'credentials')
            with open(validated, mode) as stream:
                if mode == 'rb':
                    stream.read()
                else:
                    stream.write(b'UNEXPECTED_TEST_WRITE\n')
            rejected.append(False)
        except TestRootViolation:
            rejected.append(True)
    host_read_blocked = False
    host_write_blocked = False
    try:
        Path(request['host_canary']).read_bytes()
    except (PermissionError, FileNotFoundError):
        host_read_blocked = True
    try:
        # Only the synthetic parent sentinel, never a host credential location.
        with open(request['host_canary'], 'r+b') as stream:
            stream.write(b'UNEXPECTED_TEST_WRITE\n')
    except (PermissionError, FileNotFoundError):
        host_write_blocked = True
    network_blocked = False
    network_errno = None
    try:
        with socket.socket() as connection:
            connection.settimeout(3)
            connection.connect(('192.0.2.1', 443))
    except OSError as error:
        network_errno = error.errno
        network_blocked = error.errno in {
            errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EPERM, errno.EACCES,
            errno.ENETDOWN, 10051, 10065, 10013, 10050,
        }
    summary = {
        'linked_read_rejected': rejected[0], 'linked_write_rejected': rejected[1],
        'external_target_unchanged': digest(sentinel.read_bytes()) == before,
        'host_canary_read_blocked': host_read_blocked,
        'host_canary_write_blocked': host_write_blocked,
        'network_blocked': network_blocked, 'network_errno': network_errno,
    }
    summary['passed'] = all(value for key, value in summary.items()
                            if key != 'network_errno')
    print(json.dumps(summary))
    return 0 if summary['passed'] else 1


def clean_environment(root):
    return {
        'HOME': str(root / 'home'), 'USERPROFILE': str(root / 'home'),
        'TMPDIR': str(root / 'tmp'), 'TMP': str(root / 'tmp'),
        'TEMP': str(root / 'tmp'), 'PATH': '/usr/bin:/bin',
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONIOENCODING': 'utf-8',
        'LANG': 'en_US.UTF-8',
    }


def parse_payload(result):
    # Accept exactly one JSON object; never reproduce arbitrary child output.
    data = json.loads(result)
    allowed = {
        'linked_read_rejected', 'linked_write_rejected', 'external_target_unchanged',
        'host_canary_read_blocked', 'host_canary_write_blocked', 'network_blocked',
        'network_errno', 'passed',
    }
    assert isinstance(data, dict) and set(data) == allowed
    assert all(type(value) is bool for key, value in data.items() if key != 'network_errno')
    assert data['network_errno'] is None or type(data['network_errno']) is int
    return data


def windows_probe(source, owned, host_canary):
    # Preparation may download a public runtime. The payload has no network.
    tag = 'python:3.13.15-windowsservercore-ltsc2025'
    execute(['docker', 'pull', tag], timeout=900)
    image_id = execute(['docker', 'image', 'inspect', '--format', '{{.Id}}', tag]).decode().strip()
    assert re.fullmatch(r'sha256:[0-9a-f]{64}', image_id)
    request = owned / 'request.json'
    request.write_text(json.dumps({'root': 'C:\\test-root', 'host_canary': str(host_canary)}), encoding='utf-8')
    command = ['docker', 'create', '--isolation', 'process', '--network', 'none',
               '--workdir', 'C:\\probe', '--env', 'HOME=C:\\test-root\\home',
               '--env', 'USERPROFILE=C:\\test-root\\home',
               '--env', 'TEMP=C:\\test-root\\tmp', '--env', 'TMP=C:\\test-root\\tmp',
               image_id, 'python', '-I', '-S', 'C:\\probe\\native_probe.py',
               '--payload', 'C:\\probe\\request.json']
    container_id = execute(command).decode().strip()
    assert re.fullmatch(r'[0-9a-f]{64}', container_id)
    try:
        state = json.loads(execute(['docker', 'inspect', container_id]))[0]
        assert state['HostConfig']['NetworkMode'] == 'none' and state['Mounts'] == []
        bundle = owned / 'probe'
        bundle.mkdir()
        for name, path in [('native_probe.py', source / 'native_probe.py'),
                           ('test_isolation.py', source / 'test_isolation.py'),
                           ('request.json', request)]:
            shutil.copyfile(path, bundle / name)
        # A stopped container has not created its configured working directory.
        # Copy the whole directory into the existing drive root before starting.
        execute(['docker', 'cp', str(bundle), container_id + ':C:\\'])
        result = subprocess.run(['docker', 'start', '--attach', container_id],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
        data = parse_payload(result.stdout)
        state = json.loads(execute(['docker', 'inspect', container_id]))[0]
        data.update({'container_exit_code': state['State']['ExitCode'],
                     'no_mounts': state['Mounts'] == [],
                     'network_mode_none': state['HostConfig']['NetworkMode'] == 'none',
                     'runtime_image_id': image_id})
        data['passed'] = data['passed'] and result.returncode == 0 and state['State']['ExitCode'] == 0
        return data
    finally:
        # Only the exact container created above belongs to this probe.
        execute(['docker', 'rm', '--force', container_id])


def macos_probe(source, owned, host_canary):
    root = owned / 'allowed'
    root.mkdir()
    for name in ('home', 'tmp'):
        (root / name).mkdir()
    for name in ('native_probe.py', 'test_isolation.py'):
        shutil.copyfile(source / name, root / name)
    request = root / 'request.json'
    request.write_text(json.dumps({'root': str(root), 'host_canary': str(host_canary)}), encoding='utf-8')
    runtime = Path(sys.base_prefix).resolve(strict=True)
    executable = Path(sys.executable).resolve(strict=True)
    def literal(path):
        raw = str(path)
        assert re.fullmatch(r'[A-Za-z0-9_./-]+', raw)
        return '"' + raw + '"'
    read_roots = [Path('/System'), Path('/usr'), Path('/bin'), runtime, root]
    rules = ['(version 1)', '(deny default)', '(allow process*)', '(allow sysctl-read)',
             '(deny network*)', '(allow file-read* (literal "/"))']
    rules += ['(allow file-read* (subpath ' + literal(path) + '))' for path in read_roots]
    rules += ['(allow file-write* (subpath ' + literal(root) + '))']
    for path in ['/dev/null', '/dev/urandom', '/dev/random']:
        rules.append('(allow file-read* file-write* (literal ' + literal(path) + '))')
    for path in sorted(set(root.parents) | set(runtime.parents) | {executable}, key=str):
        rules.append('(allow file-read-metadata (literal ' + literal(path) + '))')
    profile = owned / 'profile.sb'
    profile.write_text('\n'.join(rules) + '\n', encoding='utf-8')
    result = subprocess.run(['/usr/bin/sandbox-exec', '-f', str(profile), str(executable),
                             '-I', '-S', str(root / 'native_probe.py'), '--payload', str(request)],
                            env=clean_environment(root), cwd=root,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
    if not result.stdout:
        raise RuntimeError(json.dumps({'exit_code': result.returncode,
                                      'stderr_sha256': digest(result.stderr)}))
    data = parse_payload(result.stdout)
    data.update({'sandbox_exit_code': result.returncode,
                 'default_deny_profile': True, 'profile_sha256': digest(profile.read_bytes())})
    data['passed'] = data['passed'] and result.returncode == 0
    return data


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--payload':
        return payload(sys.argv[2])
    # Fail before creating canaries, invoking Docker, or executing any payload.
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
        raise SystemExit('Probe controller requires a disposable GitHub-hosted runner')
    source = Path(__file__).resolve().parent
    base = Path('C:/') if sys.platform == 'win32' else Path('/private/tmp')
    owned = base / ('kirocrew-native-probe-' + uuid.uuid4().hex)
    owned.mkdir()
    host_canary = owned / 'synthetic-host-sentinel'
    host_canary.write_bytes(b'FAKE_HOST_CANARY_NO_REAL_CREDENTIAL\n')
    before = digest(host_canary.read_bytes())
    summary = {'platform': sys.platform, 'passed': False}
    try:
        if sys.platform == 'win32':
            summary.update(windows_probe(source, owned, host_canary))
        elif sys.platform == 'darwin':
            summary.update(macos_probe(source, owned, host_canary))
        else:
            raise RuntimeError('Unsupported native runner')
    except Exception as error:
        summary.update({'passed': False, 'failure_type': type(error).__name__,
                        'failure_fingerprint': digest(str(error).encode())})
        frame = error.__traceback__
        while frame.tb_next is not None:
            frame = frame.tb_next
        summary['failure_line'] = frame.tb_lineno
        if isinstance(error, RuntimeError):
            try:
                detail = json.loads(str(error))
            except ValueError:
                detail = {}
            if set(detail) <= {'exit_code', 'stderr_sha256', 'operation', 'diagnostic_tags'}:
                summary.update(detail)
    summary['host_canary_unchanged'] = digest(host_canary.read_bytes()) == before
    summary['passed'] = summary['passed'] and summary['host_canary_unchanged']
    (source / 'probe-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary))
    return 0 if summary['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
