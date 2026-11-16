import argparse
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import install
import patch as patcher


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'original'
        self.source.mkdir()
        (self.source / 'app.asar').write_bytes(b'original')
        self.target = self.root / 'user files' / 'dynamic tabs'
        self.args = argparse.Namespace(source=self.source, electron='electron21',
            prefix=self.target, desktop_dir=self.root / 'desktop files')

    def run_install(self, builder=None):
        def fake_build(source, target):
            target.write_bytes(b'patched')
        with patch('install.shutil.which', return_value='/usr/bin/electron21'), \
             patch('install.subprocess.run', return_value=subprocess.CompletedProcess([], 0, 'v21.4.4\n', '')), \
             patch('install.build', side_effect=builder or fake_build):
            install.install(self.args)

    def test_install_reinstall_and_uninstall(self):
        self.run_install()
        self.assertEqual((self.target / 'app.asar').read_bytes(), b'patched')
        self.assertEqual((self.source / 'app.asar').read_bytes(), b'original')
        subprocess.run(['sh', '-n', str(self.target / 'launch')], check=True)
        desktop = self.args.desktop_dir / (install.APP_ID + '.desktop')
        self.assertIn('Exec="', desktop.read_text())
        self.run_install()
        install.uninstall(self.args)
        self.assertFalse(self.target.exists())
        self.assertFalse(desktop.exists())
        self.assertTrue((self.source / 'app.asar').exists())

    def test_failed_patch_preserves_previous_install(self):
        self.run_install()
        def fail(source, target):
            raise RuntimeError('Unsupported version')
        with self.assertRaisesRegex(RuntimeError, 'Unsupported version'):
            self.run_install(fail)
        self.assertEqual((self.target / 'app.asar').read_bytes(), b'patched')

    def test_unmanaged_directory_is_preserved(self):
        self.target.mkdir(parents=True)
        personal = self.target / 'personal.txt'
        personal.write_text('keep')
        with self.assertRaisesRegex(RuntimeError, 'unmanaged'):
            self.run_install()
        with self.assertRaisesRegex(RuntimeError, 'No managed installation'):
            install.uninstall(self.args)
        self.assertEqual(personal.read_text(), 'keep')

    def test_source_directory_is_rejected(self):
        self.args.prefix = self.source
        with self.assertRaisesRegex(RuntimeError, 'separate'):
            self.run_install()

    def test_anchor_mismatch_fails_closed(self):
        with self.assertRaises(RuntimeError):
            patcher.replace_once('missing', 'expected', 'new')
        with self.assertRaises(RuntimeError):
            patcher.replace_once('expected expected', 'expected', 'new')

    def test_helper_behavior_without_termius(self):
        script = patcher.HELPER + r'''
const assert=require('node:assert/strict');
const local={protocol:'local',cwd:'/home/user/backend',connectionProcess:'succeeded',activeCommand:{isDurational:true,command:'cd ~/backend && npm run start:dev -- --watch'}};
assert.equal(termiusDynamicTabTitle('Local Terminal',[local]),'backend · npm run start:dev');
local.activeCommand.command='ciadpi -Kt,h -d1 -s0+s -d3+s';
assert.equal(termiusDynamicTabTitle('Local Terminal',[local]),'backend · ciadpi');
local.activeCommand.isDurational=false;
assert.equal(termiusDynamicTabTitle('Local Terminal',[local]),local.cwd);
assert.equal(termiusTabUsesPath(local.cwd,[local]),true);
local.activeCommand.isDurational=true;
local.activeCommand.exitCode='0';
assert.equal(termiusDynamicTabTitle('Local Terminal',[local]),local.cwd);
const remote={...local,protocol:'ssh',activeCommand:{command:'npm run dev -- --watch'}};
assert.equal(termiusDynamicTabTitle('server',[remote]),'server · npm run dev');
assert.equal(termiusDynamicTabTitle('manual',[local],true),'manual');
'''
        subprocess.run(['node', '-e', script], check=True)


if __name__ == '__main__':
    unittest.main()
