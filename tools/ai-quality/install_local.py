"""Install pinned tools without inheriting application credentials."""
import subprocess
import sys
import venv
from pathlib import Path
from local_environment import tool_environment

root = Path(__file__).resolve().parent
node_directory = Path.home() / '.cache' / 'codex-runtimes' / 'codex-primary-runtime' / 'dependencies' / 'node' / 'bin'
env = tool_environment(root, node_directory)
venv_directory = root / '.venv'
if not (venv_directory / 'Scripts' / 'python.exe').exists():
    venv.EnvBuilder(with_pip=True).create(venv_directory)
python = venv_directory / 'Scripts' / 'python.exe'
commands = [
    [str(python), '-m', 'pip', 'install', '--disable-pip-version-check', '-r', str(root / 'requirements.txt')],
    [str(node_directory / 'node.exe'), str(node_directory.parent / 'node_modules' / 'pnpm' / 'bin' / 'pnpm.cjs'), 'install', '--frozen-lockfile'],
]
for command in commands:
    completed = subprocess.run(command, cwd=root, env=env)
    if completed.returncode:
        sys.exit(completed.returncode)
print('Local tool installation completed. No model requests were made by this installer.')
