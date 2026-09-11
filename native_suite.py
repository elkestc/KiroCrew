"""Prepare public runtimes, then launch source copies in native offline boundaries."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

from native_probe import digest, execute


def environment(root, runtime_paths):
    home = root / 'homes' / 'collection'
    env = {
        'HOME': str(home), 'USERPROFILE': str(home), 'HOMEPATH': str(home),
        'USER': 'test', 'USERNAME': 'test', 'LOGNAME': 'test',
        'TMPDIR': str(root / 'tmp'), 'TMP': str(root / 'tmp'), 'TEMP': str(root / 'tmp'),
        'XDG_CONFIG_HOME': str(home / '.config'), 'XDG_CACHE_HOME': str(home / '.cache'),
        'APPDATA': str(home / 'AppData/Roaming'), 'LOCALAPPDATA': str(home / 'AppData/Local'),
        'KIROCREW_HOME': str(home / '.kiro/crew'), 'KIROCREW_TEST_ROOT': str(root),
        'KIROCREW_TELEMETRY': '0', 'KIROCREW_SKIP_MODEL_DOWNLOAD': '1',
        'KIROCREW_MAX_TEST_WORKERS': '2', 'MDNB_GIT_TIMEOUT_SEC': '120',
        'PYTHONPATH': os.pathsep.join(map(str, [root / 'repo', root / 'repo/src'])),
        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUNBUFFERED': '1', 'PYTHONIOENCODING': 'utf-8',
        'LANG': 'en_US.UTF-8', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
        'PATH': os.pathsep.join(map(str, runtime_paths)),
    }
    if sys.platform == 'win32':
        env.update({'SystemRoot': r'C:\Windows', 'WINDIR': r'C:\Windows',
                    'COMSPEC': r'C:\Windows\System32\cmd.exe', 'PATHEXT': '.COM;.EXE;.BAT;.CMD'})
    return env


def prepare_source(source, root):
    for name in ('homes/collection', 'tmp', 'results'):
        (root / name).mkdir(parents=True)
    shutil.copytree(source / 'repo', root / 'repo', symlinks=False)
    for name in ('native_probe.py', 'native_entry.py'):
        shutil.copyfile(source / name, root / name)
    shutil.copyfile(root / 'repo/test_isolation.py', root / 'test_isolation.py')
    shutil.copyfile(root / 'repo/native_test_boundary.py', root / 'native_test_boundary.py')
    modes = json.loads((source / 'source-provenance.json').read_text())['file_modes']
    if sys.platform != 'win32':
        for name, mode in modes.items():
            (root / 'repo' / name).chmod(mode)


def windows(source, owned, canary, group):
    context = owned / 'context'
    root = context / 'test-root'
    prepare_source(source, root)
    # Copy only the public tool installation, never a profile or Git metadata.
    git_root = Path(r'C:\Program Files\Git')
    assert git_root.is_dir() and not git_root.is_symlink()
    shutil.copytree(git_root, context / 'git')
    dockerfile = context / 'Dockerfile'
    dockerfile.write_text('''FROM python:3.12-windowsservercore-ltsc2025
COPY git C:/runtime/git
COPY test-root C:/test-root
WORKDIR C:/test-root/repo
RUN python -m pip install uv
RUN uv pip install --system -e ".[voice,desktop]" --group dev
''')
    image_file = owned / 'image-id'
    execute(['docker', 'build', '--iidfile', str(image_file), str(context)], timeout=1800)
    image = image_file.read_text().strip()
    assert re.fullmatch(r'sha256:[0-9a-f]{64}', image)
    child_root = Path(r'C:\test-root')
    env = environment(child_root, [r'C:\Python', r'C:\Python\Scripts', r'C:\runtime\git\cmd',
                                  r'C:\runtime\git\usr\bin', r'C:\Windows\System32', r'C:\Windows'])
    env['KIROCREW_TEST_HOST_CANARY'] = str(canary)
    command = ['docker', 'create', '--isolation', 'process', '--network', 'none',
               '--workdir', str(child_root / 'repo')]
    for key, value in env.items():
        command += ['--env', key + '=' + value]
    command += [image, r'C:\Python\python.exe', r'C:\test-root\native_entry.py', group]
    container = execute(command).decode().strip()
    assert re.fullmatch(r'[0-9a-f]{64}', container)
    try:
        state = json.loads(execute(['docker', 'inspect', container]))[0]
        assert state['Mounts'] == [] and state['HostConfig']['NetworkMode'] == 'none'
        log = owned / 'launcher.log'
        with log.open('wb') as stream:
            result = subprocess.run(['docker', 'start', '--attach', container],
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=2400)
        state = json.loads(execute(['docker', 'inspect', container]))[0]
        execute(['docker', 'cp', container + ':C:\\test-root\\results', str(owned / 'results')])
        return {'exit_code': state['State']['ExitCode'], 'launcher_exit_code': result.returncode,
                'no_mounts': state['Mounts'] == [], 'network_mode_none': state['HostConfig']['NetworkMode'] == 'none',
                'runtime_image_id': image, 'launcher_log_sha256': digest(log.read_bytes())}
    finally:
        execute(['docker', 'rm', '--force', container])


def macos(source, owned, canary):
    root = owned / 'test-root'
    prepare_source(source, root)
    runtime = owned / 'runtime'
    prep = owned / 'prep'
    prep.mkdir()
    env = environment(root, ['/usr/bin', '/bin', '/opt/homebrew/bin'])
    env['UV_PYTHON_INSTALL_DIR'] = str(runtime)
    env['UV_CACHE_DIR'] = str(prep / 'cache')
    uv = shutil.which('uv')
    assert uv
    execute([uv, 'python', 'install', '--no-config', '--no-bin', '3.12'], env=env, cwd=prep, timeout=300)
    python = Path(execute([uv, 'python', 'find', '--managed-python', '3.12'], env=env, cwd=prep).decode().strip())
    assert python.resolve().is_relative_to(runtime)
    execute([uv, 'pip', 'install', '--python', str(python), '-e', '.[voice,desktop]', '--group', 'dev'],
            env=env, cwd=root / 'repo', timeout=600)
    env['PATH'] = str(python.parent) + ':/usr/bin:/bin:/opt/homebrew/bin'
    env['KIROCREW_TEST_HOST_CANARY'] = str(canary)
    env.pop('UV_CACHE_DIR')
    env.pop('UV_PYTHON_INSTALL_DIR')
    def literal(path):
        assert re.fullmatch(r'[A-Za-z0-9_./-]+', str(path))
        return '"' + str(path) + '"'
    rules = ['(version 1)', '(deny default)', '(allow process-exec)', '(allow process-fork)',
             '(allow process-info* (target same-sandbox))', '(allow signal (target same-sandbox))',
             '(allow sysctl-read)', '(deny network*)', '(allow file-read* (literal "/"))',
             '(allow system-socket (socket-domain AF_UNIX))',
             '(allow network-bind (local unix-socket (subpath ' + literal(root) + ')))',
             '(allow network-outbound (remote unix-socket (subpath ' + literal(root) + ')))']
    for path in ['/System', '/usr', '/bin', '/opt/homebrew', '/Library/Developer/CommandLineTools', runtime, root]:
        rules.append('(allow file-read* (subpath ' + literal(path) + '))')
    rules.append('(allow file-write* (subpath ' + literal(root) + '))')
    for path in ['/dev/null', '/dev/urandom', '/dev/random']:
        rules.append('(allow file-read* file-write* (literal ' + literal(path) + '))')
    for path in sorted(set(root.parents) | set(runtime.parents), key=str):
        rules.append('(allow file-read-metadata (literal ' + literal(path) + '))')
    profile = owned / 'profile.sb'
    profile.write_text('\n'.join(rules) + '\n')
    log = owned / 'launcher.log'
    with log.open('wb') as stream:
        result = subprocess.run(['/usr/bin/sandbox-exec', '-f', str(profile), str(python),
                                 str(root / 'native_entry.py')], cwd=root / 'repo', env=env,
                                stdout=stream, stderr=subprocess.STDOUT, timeout=2400)
    shutil.copytree(root / 'results', owned / 'results')
    return {'exit_code': result.returncode, 'default_deny_profile': True,
            'profile_sha256': digest(profile.read_bytes()), 'launcher_log_sha256': digest(log.read_bytes())}


def main():
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
        raise SystemExit('Native evaluation requires a disposable GitHub-hosted runner')
    source = Path(__file__).resolve().parent
    owned = (Path('C:/') if sys.platform == 'win32' else Path('/private/tmp')) / ('kct-' + uuid.uuid4().hex[:8])
    owned.mkdir()
    canary = owned / 'synthetic-host-sentinel'
    canary.write_bytes(b'FAKE_HOST_CANARY_NO_REAL_CREDENTIAL\n')
    before = digest(canary.read_bytes())
    summary = {'platform': sys.platform, 'passed': False}
    try:
        summary.update(windows(source, owned, canary, sys.argv[1]) if sys.platform == 'win32'
                       else macos(source, owned, canary))
        report = owned / 'results/suite-summary.json'
        if report.is_file():
            summary['suites'] = json.loads(report.read_text())
            summary['passed'] = summary['exit_code'] == 0 and all(item['passed'] for item in summary['suites'])
    except Exception as error:
        summary.update({'failure_type': type(error).__name__,
                        'failure_fingerprint': digest(str(error).encode())})
        frame = error.__traceback__
        while frame.tb_next:
            frame = frame.tb_next
        summary['failure_line'] = frame.tb_lineno
        if isinstance(error, RuntimeError):
            try:
                detail = json.loads(str(error))
            except ValueError:
                detail = {}
            if set(detail) <= {'exit_code', 'stderr_sha256', 'operation', 'diagnostic_tags'}:
                summary.update(detail)
    summary['host_canary_unchanged'] = digest(canary.read_bytes()) == before
    summary['passed'] = summary['passed'] and summary['host_canary_unchanged']
    (source / 'native-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary))
    return int(not summary['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
