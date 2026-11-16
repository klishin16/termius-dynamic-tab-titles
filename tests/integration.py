#!/usr/bin/env python3
"""Check the patch against a real local Termius archive; nothing is installed."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from patch import build, entries, FISH


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('/opt/termius/app.asar'))
    args = parser.parse_args()
    before = hashlib.sha256(args.source.read_bytes()).digest()
    with tempfile.TemporaryDirectory(prefix='dynamic-tabs-test-') as tmp:
        root = Path(tmp)
        archive = root / 'app.asar'
        check = root / 'check'
        build(args.source, archive, check)
        subprocess.run(['node', str(Path(__file__).with_name('check.cjs')), str(check)], check=True)
        for bundle in check.glob('*.mjs'):
            subprocess.run(['node', '--check', str(bundle)], check=True)
        raw = archive.read_bytes()
        _, header_size, _, json_size = struct.unpack_from('<4I', raw)
        header = json.loads(raw[16:16 + json_size])
        changed = json.loads((root / 'build.json').read_text())['changed_files']
        for name, item in entries(header):
            if item.get('unpacked'):
                if name not in changed:
                    continue
                data = (root / 'app.asar.unpacked' / name).read_bytes()
            elif 'offset' in item:
                start = 8 + header_size + int(item['offset'])
                data = raw[start:start + item['size']]
            else:
                continue
            assert len(data) == item['size'], name
            integrity = item.get('integrity')
            if integrity:
                assert hashlib.sha256(data).hexdigest() == integrity['hash'], name
                block_size = integrity['blockSize']
                assert [hashlib.sha256(data[i:i+block_size]).hexdigest() for i in range(0,len(data),block_size)] == integrity['blocks'], name
        fish = root / 'app.asar.unpacked' / FISH
        subprocess.run(['fish', '--no-config', '--no-execute', str(fish)], check=True)
        script = fish.read_text()
        functions = script[script.index('function _termius_encode'):script.index('function _termius_command_exited')]
        command = 'ciadpi ' + '-s443+s ' * 100
        result = subprocess.run(['fish', '--no-config', '-c', functions + '\n_termius_command_started "$argv[1]"', '--', command], capture_output=True, check=True)
        events = re.findall(rb'\x1b\]4545;CommandStarted;([^\x07]+)\x07', result.stdout)
        assert len(events) == 1
        assert base64.b64decode(events[0]).decode() == command
    assert hashlib.sha256(args.source.read_bytes()).digest() == before
    print('PASS: real bundles, ASAR offsets and integrity, long fish commands; original unchanged')


if __name__ == '__main__':
    main()
