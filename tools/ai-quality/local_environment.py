"""A credential-free environment for installation and offline tool checks."""
import os
from pathlib import Path

def tool_environment(root: Path, node_directory: Path) -> dict[str, str]:
    env = {
        key: value for key, value in os.environ.items()
        if not key.upper().startswith(('APP_', 'AI_', 'PROXYAPI_', 'CHEAPAI_', 'YANDEX_', 'YC_', 'SMTP_', 'ELEVENLABS_', 'OPENAI_', 'ANTHROPIC_', 'GOOGLE_', 'AWS_', 'AZURE_'))
        and not any(word in key.upper() for word in ('SECRET', 'PASSWORD', 'TOKEN', 'API_KEY'))
    }
    env.update({
        'PATH': str(node_directory) + os.pathsep + env.get('PATH', ''),
        'PROMPTFOO_DISABLE_TELEMETRY': '1',
        'PROMPTFOO_DISABLE_UPDATE': '1',
        'PROMPTFOO_DISABLE_REMOTE_GENERATION': 'true',
        'PROMPTFOO_CONFIG_DIR': str(root / 'output' / 'promptfoo-home'),
        'PROMPTFOO_CACHE_PATH': str(root / 'output' / 'promptfoo-cache'),
        'PYTHONUTF8': '1',
        'CI': '1',
    })
    return env
