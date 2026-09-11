"""Entry point executed only inside the native OS boundary."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


def main():
    root = Path(os.environ['KIROCREW_TEST_ROOT'])
    repo = root / 'repo'
    sys.path[:0] = [str(root), str(repo), str(repo / 'src')]
    from native_probe import payload
    request = root / 'probe-request.json'
    request.write_text(json.dumps({'root': str(root / 'boundary-probe'),
                                  'host_canary': os.environ['KIROCREW_TEST_HOST_CANARY']}))
    if payload(str(request)):
        return 1
    from test_isolation import require_isolated_environment
    require_isolated_environment()
    os.chdir(repo)
    # No parent metadata, config, hooks, history, remotes, or credentials.
    for args in (['init', '--template=', '--initial-branch=isolated-fixture', '.'],
                 ['add', '--force', '--all', '--', '.'],
                 ['commit', '--quiet', '-m', 'Disposable source fixture']):
        result = subprocess.run(['git', '-c', 'core.hooksPath=' + os.devnull,
                        '-c', 'core.autocrlf=false', '-c', 'commit.gpgsign=false',
                        '-c', 'user.name=Disposable Test', '-c', 'user.email=test@invalid',
                        *args], cwd=repo, capture_output=True, check=False, timeout=300)
        if result.returncode:
            text = result.stderr.decode('utf-8', errors='replace').lower()
            tags = ['operation not permitted', 'permission denied', 'not found',
                    'xcrun', 'xcode', 'unable to access', 'could not', 'failed to',
                    'unable to', 'dubious ownership', 'nothing to commit', 'index.lock']
            (root / 'results/startup-summary.json').write_text(json.dumps({
                'stage': 'git:' + args[0], 'exit_code': result.returncode,
                'stderr_sha256': hashlib.sha256(result.stderr).hexdigest(),
                'tags': [tag for tag in tags if tag in text]}))
            return result.returncode
    commands = []
    if sys.platform == 'darwin':
        commands.append(('canary', ['-v', '-n0', '--timeout=120',
            'test/test_socketsec.py::test_macos_check_matches_a_socket_we_connected_to_ourselves']))
        targets = set()
        for pattern in ('test_mcp_gateway_*.py', 'test_socketsec.py', 'test_platform_compat.py', 'test_offline_boundary.py',
                        'test_mcp_apps_e2e.py', 'test_pod*.py', 'test_service.py', 'test_dev_fleet_app.py'):
            targets.update(str(path.relative_to(repo)) for path in (repo / 'test').glob(pattern))
        commands.append(('native-suite', ['-q', '-n', '2', '--timeout=180', *sorted(targets)]))
    else:
        commands.append(('native-suite', ['-q', '-n', '2', '--timeout=180',
            '--max-worker-restart=0', '--splits', '4', '--group', sys.argv[1]]))
    summaries = []
    for label, args in commands:
        report = root / 'results' / (label + '.xml')
        log = root / 'results' / (label + '.log')
        with log.open('wb') as stream:
            result = subprocess.run([sys.executable, '-m', 'pytest', '--no-cov', '--color=no',
                '--tb=short', '--junitxml=' + str(report), *args], cwd=repo,
                stdout=stream, stderr=subprocess.STDOUT, check=False, timeout=2100)
        summary = {'label': label, 'exit_code': result.returncode,
                   'log_sha256': hashlib.sha256(log.read_bytes()).hexdigest()}
        if report.is_file():
            cases = list(ET.parse(report).getroot().iter('testcase'))
            summary.update({'cases': len(cases),
                'failed': sum(case.find('failure') is not None for case in cases),
                'errors': sum(case.find('error') is not None for case in cases),
                'skipped': sum(case.find('skipped') is not None for case in cases)})
            summary['failure_locations'] = []
            for case in cases:
                for kind in ('failure', 'error'):
                    failure = case.find(kind)
                    if failure is not None:
                        # Only Python locations and message fingerprints, never values.
                        body = (failure.text or '') + failure.get('message', '')
                        locations = re.findall(r'(?:test|src|scripts)[/\\][A-Za-z0-9_./\\-]+\.py:\d+', body)
                        summary['failure_locations'].append({
                            'node_sha256': hashlib.sha256((case.get('classname', '') + case.get('name', '')).encode()).hexdigest(),
                            'locations': sorted(set(locations)),
                            'message_sha256': hashlib.sha256(body.encode()).hexdigest()})
            summary['passed'] = (result.returncode == 0 and bool(cases) and
                                 not summary['failed'] and not summary['errors'] and
                                 summary['skipped'] < len(cases))
            if label == 'canary':
                summary['passed'] = summary['passed'] and len(cases) == 1 and not summary['skipped']
        else:
            summary['passed'] = False
        summaries.append(summary)
        (root / 'results' / 'suite-summary.json').write_text(json.dumps(summaries, indent=2))
    return int(not all(item['passed'] for item in summaries))


if __name__ == '__main__':
    raise SystemExit(main())
