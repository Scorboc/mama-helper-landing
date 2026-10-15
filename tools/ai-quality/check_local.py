"""Offline installation verification; deliberately has no API provider or key."""
import json
import subprocess
import sys
from pathlib import Path
from local_environment import tool_environment
from preservation import snapshot

root = Path(__file__).resolve().parent
node_directory = Path.home() / '.cache' / 'codex-runtimes' / 'codex-primary-runtime' / 'dependencies' / 'node' / 'bin'
env = tool_environment(root, node_directory)
python = root / '.venv' / 'Scripts' / 'python.exe'
entrypoint = root / 'node_modules' / 'promptfoo' / 'dist' / 'src' / 'entrypoint.js'
out = root / 'output'
out.mkdir(exist_ok=True)

commands = [
    [str(python), '-c', 'import gepa; import importlib.metadata; from gepa.optimize_anything import optimize_anything; assert callable(gepa.optimize) and callable(optimize_anything); print("GEPA " + importlib.metadata.version("gepa") + ": optimization API imports OK; no optimization started")'],
    [str(python), '-m', 'pip', 'check'],
    [str(node_directory / 'node.exe'), str(entrypoint), '--version'],
    [str(node_directory / 'node.exe'), str(entrypoint), 'eval', '-c', str(root / 'promptfooconfig.yaml'), '--no-cache', '--no-progress-bar', '-o', str(out / 'offline-smoke.json')],
]
for command in commands:
    completed = subprocess.run(command, cwd=root, env=env)
    if completed.returncode:
        sys.exit(completed.returncode)

before = json.loads((out / 'preservation-before.json').read_text(encoding='utf-8'))
after = snapshot(root)
files_unchanged = before['files'] == after['files']
data_unchanged = before['databases'] == after['databases']
result = {
    'gepa': '0.1.4',
    'promptfoo': json.loads((root / 'node_modules' / 'promptfoo' / 'package.json').read_text(encoding='utf-8'))['version'],
    'offline_smoke': 'passed',
    'model_calls': 0,
    'protected_files_checked': len(before['files']),
    'protected_files_unchanged': files_unchanged,
    'database_contents_unchanged': data_unchanged,
    'live_prompt_updated': False,
}
(out / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
if not files_unchanged or not data_unchanged:
    sys.exit('Protected state changed. Inspect locally before making preservation claims.')
