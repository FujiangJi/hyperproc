"""Build and preview documentation without executing hyperproc or its notebooks."""
from pathlib import Path
import argparse
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def run(*args):
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['generate', 'build', 'check', 'serve'])
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if args.command in ('generate', 'build'):
        run('scripts/generate.py')
    if args.command == 'build':
        run('-m', 'mkdocs', 'build', '--strict')
        run('scripts/check_site.py')
    if args.command == 'check':
        run('scripts/check_site.py')
    if args.command == 'serve':
        if not (ROOT/'site/index.html').exists():
            parser.error('Build the site first: python manage.py build')
        print(f'Local preview: http://127.0.0.1:{args.port}/ (Ctrl-C to stop)', flush=True)
        try:
            run('-m', 'http.server', str(args.port), '--bind', '127.0.0.1', '--directory', str(ROOT/'site'))
        except KeyboardInterrupt:
            pass

if __name__ == '__main__':
    main()
