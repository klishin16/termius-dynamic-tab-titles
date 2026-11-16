#!/usr/bin/env python3
"""Install a user-owned, patched Termius copy without changing the system app."""
import argparse
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile

from patch import build

APP_ID = 'termius-dynamic-tab-titles'
MARKER = '.dynamic-tab-titles-install.json'


def data_home():
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share'))


def desktop_quote(value):
    # Desktop Exec is not shell syntax. Escape its reserved characters separately.
    value = str(value).replace('%', '%%')
    for char in ('\\', '"', '`', '$'):
        value = value.replace(char, '\\' + char)
    return '"' + value + '"'


def managed(path):
    marker = path / MARKER
    return marker.is_file() and json.loads(marker.read_text()).get('app_id') == APP_ID


def install(args):
    if sys.platform != 'linux':
        raise RuntimeError('Only Linux with an external Electron 21 runtime is supported')
    source = args.source.expanduser().resolve()
    if source.is_dir():
        source /= 'app.asar'
    if not source.is_file():
        raise RuntimeError(f'Cannot find {source}; use --source /path/to/app.asar')
    electron = shutil.which(args.electron)
    if not electron:
        raise RuntimeError(f'Cannot find Electron runtime {args.electron!r}; use --electron /path/to/electron21')
    runtime_version = subprocess.run([electron, '--version'], capture_output=True, text=True, timeout=15)
    version = runtime_version.stdout.strip()
    if runtime_version.returncode or not version.startswith('v21.'):
        raise RuntimeError(f'Expected Electron 21; --version returned {version!r} (exit {runtime_version.returncode})')
    target = args.prefix.expanduser().resolve()
    if target == source.parent or target in source.parents or source.parent in target.parents:
        raise RuntimeError('Installation directory must be separate from the original application')
    if target.exists() and not managed(target):
        raise RuntimeError(f'Refusing to replace an unmanaged directory: {target}')
    desktop_dir = args.desktop_dir.expanduser().resolve()
    desktop = desktop_dir / (APP_ID + '.desktop')
    if desktop.exists() and 'X-Dynamic-Tab-Titles=true' not in desktop.read_text():
        raise RuntimeError(f'Refusing to replace an unrelated launcher: {desktop}')
    target.parent.mkdir(parents=True, exist_ok=True)
    # Build and validate before replacing a previous installation.
    with tempfile.TemporaryDirectory(prefix='.dynamic-tabs-', dir=target.parent) as tmp:
        staging = Path(tmp) / 'app'
        staging.mkdir()
        unpacked = Path(str(source) + '.unpacked')
        if unpacked.is_dir():
            shutil.copytree(unpacked, staging / 'app.asar.unpacked')
        build(source, staging / 'app.asar')
        for name in ('LICENSE', 'app-update.yml', 'package-type', 'termius.png'):
            if (source.parent / name).is_file():
                shutil.copy2(source.parent / name, staging / name)
        launcher = staging / 'launch'
        launcher.write_text('#!/bin/sh\nset -eu\nexec ' + shlex.quote(electron) + ' ' + shlex.quote(str(target / 'app.asar')) + ' "$@"\n')
        launcher.chmod(0o755)
        (staging / MARKER).write_text(json.dumps({'app_id': APP_ID, 'desktop': str(desktop)}, indent=2) + '\n')
        previous = Path(tmp) / 'previous'
        if target.exists():
            target.rename(previous)
        try:
            staging.rename(target)
        except OSError:
            if previous.exists():
                previous.rename(target)
            raise
    desktop_dir.mkdir(parents=True, exist_ok=True)
    icon = target / 'termius.png'
    desktop.write_text(
        '[Desktop Entry]\nName=Termius Dynamic Tab Titles\n'
        'Comment=Termius with running commands and directories in tab titles\n'
        f'Exec={desktop_quote(target / "launch")} %U\n'
        f'Icon={icon if icon.exists() else "utilities-terminal"}\n'
        'Terminal=false\nType=Application\nStartupWMClass=Termius\nCategories=Utility;\n'
        'X-Dynamic-Tab-Titles=true\n')
    print(f'Installed: {target}\nLaunch: {target / "launch"}\nFully close Termius before launching this copy.')


def uninstall(args):
    target = args.prefix.expanduser().resolve()
    if not managed(target):
        raise RuntimeError(f'No managed installation at {target}')
    metadata = json.loads((target / MARKER).read_text())
    desktop = Path(metadata['desktop'])
    if desktop.is_file() and 'X-Dynamic-Tab-Titles=true' in desktop.read_text():
        desktop.unlink()
    shutil.rmtree(target)
    print(f'Removed: {target}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='action', required=True)
    for action in ('install', 'uninstall'):
        command = actions.add_parser(action)
        command.add_argument('--prefix', type=Path, default=data_home() / APP_ID)
        if action == 'install':
            command.add_argument('--source', type=Path, default=Path('/opt/termius'))
            command.add_argument('--electron', default='electron21')
            command.add_argument('--desktop-dir', type=Path, default=data_home() / 'applications')
    args = parser.parse_args()
    try:
        (install if args.action == 'install' else uninstall)(args)
    except (OSError, ValueError, RuntimeError, KeyError, subprocess.SubprocessError) as error:
        parser.exit(1, f'Error: {error}\n')


if __name__ == '__main__':
    main()
