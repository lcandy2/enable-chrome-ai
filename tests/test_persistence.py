import json
import os
import plistlib
import stat
import sys
import tempfile
import unittest
from argparse import Namespace
from unittest import mock

import chrome_processes
import launchd
import main
from launchd import build_launch_agent


class PersistenceTests(unittest.TestCase):
    def make_local_state(self, value):
        temporary_directory = tempfile.TemporaryDirectory()
        path = os.path.join(temporary_directory.name, 'Local State')
        with open(path, 'w', encoding='utf-8') as fp:
            json.dump(value, fp)
        return temporary_directory, path

    def test_missing_consistency_is_created(self):
        directory, path = self.make_local_state({
            'variations_country': 'us',
            'is_glic_eligible': True,
        })
        self.addCleanup(directory.cleanup)

        self.assertTrue(main.local_state_needs_patch(directory.name, '150', 'us'))
        main.patch_local_state(directory.name, '150', 'us')

        with open(path, 'r', encoding='utf-8') as fp:
            state = json.load(fp)
        self.assertEqual(
            state['variations_permanent_consistency_country'], ['150', 'us'])
        self.assertFalse(main.local_state_needs_patch(directory.name, '150', 'us'))

    def test_atomic_write_preserves_permissions(self):
        directory, path = self.make_local_state({'old': True})
        self.addCleanup(directory.cleanup)
        os.chmod(path, 0o600)

        main.write_json_atomically(path, {'new': True})

        with open(path, 'r', encoding='utf-8') as fp:
            self.assertEqual(json.load(fp), {'new': True})
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)

    def test_failed_atomic_write_keeps_original_file(self):
        directory, path = self.make_local_state({'old': True})
        self.addCleanup(directory.cleanup)

        with mock.patch('main.json.dump', side_effect=OSError('disk full')):
            with self.assertRaisesRegex(OSError, 'disk full'):
                main.write_json_atomically(path, {'new': True})

        with open(path, 'r', encoding='utf-8') as fp:
            self.assertEqual(json.load(fp), {'old': True})
        self.assertEqual(os.listdir(directory.name), ['Local State'])

    def test_country_is_normalized_and_validated(self):
        self.assertEqual(main.parse_country('US'), 'us')
        with self.assertRaisesRegex(Exception, 'two-letter'):
            main.parse_country('usa')

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS-specific command')
    def test_restart_uses_launch_services(self):
        executable = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        self.assertEqual(
            chrome_processes.chrome_restart_command(executable),
            ['open', '/Applications/Google Chrome.app'],
        )

    def test_launch_agent_is_fixed_to_country_and_runs_at_login(self):
        agent = build_launch_agent('us', '/venv/python', '/repo/main.py')
        plistlib.loads(plistlib.dumps(agent))
        self.assertEqual(
            agent['ProgramArguments'],
            ['/venv/python', '/repo/main.py', '--country', 'us', '--yes'],
        )
        self.assertTrue(agent['RunAtLoad'])

    @mock.patch('launchd.sys.platform', 'darwin')
    @mock.patch('launchd._launchctl')
    def test_launch_agent_install_is_loadable(self, launchctl):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)

        with mock.patch.dict(os.environ, {'HOME': directory.name}):
            launchd.install_launch_agent('us', '/repo/main.py')
            agent_path = launchd.launch_agent_path()
            with open(agent_path, 'rb') as fp:
                agent = plistlib.load(fp)

        self.assertEqual(agent['Label'], launchd.LABEL)
        self.assertEqual(agent['ProgramArguments'][-3:], ['--country', 'us', '--yes'])
        domain = 'gui/%d' % os.getuid()
        self.assertEqual(
            launchctl.call_args_list,
            [
                mock.call('bootout', domain, agent_path, check=False),
                mock.call('bootstrap', domain, agent_path),
            ],
        )

    @mock.patch('chrome_processes.psutil.wait_procs', return_value=([], []))
    @mock.patch('chrome_processes.psutil.process_iter')
    def test_shutdown_ignores_chrome_helpers(self, process_iter, wait_procs):
        helper = mock.Mock()
        helper.name.return_value = 'Google Chrome Helper'
        process_iter.return_value = [helper]

        self.assertEqual(chrome_processes.shutdown_chrome(), set())
        helper.terminate.assert_not_called()
        wait_procs.assert_called_once_with([], timeout=10)

    @mock.patch('chrome_processes.sys.platform', 'win32')
    def test_parent_disappearing_does_not_crash(self):
        process = mock.Mock()
        process.name.return_value = 'chrome.exe'
        process.parent.side_effect = chrome_processes.psutil.NoSuchProcess(123)

        self.assertFalse(chrome_processes.is_top_level_chrome(process))

    @mock.patch('chrome_processes.sys.platform', 'win32')
    def test_parentless_windows_process_is_top_level(self):
        process = mock.Mock()
        process.name.return_value = 'chrome.exe'
        process.parent.return_value = None

        self.assertTrue(chrome_processes.is_top_level_chrome(process))

    @mock.patch('chrome_processes.sys.platform', 'darwin')
    @mock.patch('chrome_processes.psutil.wait_procs')
    @mock.patch('chrome_processes.psutil.process_iter')
    def test_shutdown_waits_for_main_process_and_children(
            self, process_iter, wait_procs):
        chrome = mock.Mock()
        chrome.name.return_value = 'Google Chrome'
        chrome.exe.return_value = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        child = mock.Mock()
        chrome.children.return_value = [child]
        process_iter.return_value = [chrome]
        wait_procs.return_value = ([chrome, child], [])

        self.assertEqual(
            chrome_processes.shutdown_chrome(),
            {'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'},
        )
        chrome.terminate.assert_called_once_with()
        wait_procs.assert_called_once_with([chrome, child], timeout=10)

    @mock.patch('chrome_processes.sys.platform', 'darwin')
    @mock.patch('chrome_processes.psutil.wait_procs')
    @mock.patch('chrome_processes.psutil.process_iter')
    def test_shutdown_kills_process_after_timeout(
            self, process_iter, wait_procs):
        chrome = mock.Mock()
        chrome.name.return_value = 'Google Chrome'
        chrome.exe.return_value = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        chrome.children.return_value = []
        process_iter.return_value = [chrome]
        wait_procs.side_effect = [([], [chrome]), ([chrome], [])]

        chrome_processes.shutdown_chrome()

        chrome.kill.assert_called_once_with()
        self.assertEqual(
            wait_procs.call_args_list,
            [
                mock.call([chrome], timeout=10),
                mock.call([chrome], timeout=5),
            ],
        )

    @mock.patch('chrome_processes.sys.platform', 'darwin')
    def test_macos_restart_rejects_non_bundle_executable(self):
        with self.assertRaisesRegex(ValueError, 'app bundle'):
            chrome_processes.chrome_restart_command('/usr/local/bin/chrome')

    @mock.patch('main.restart_chrome')
    @mock.patch('main.patch_local_state', side_effect=OSError('disk full'))
    @mock.patch('main.shutdown_chrome', return_value={'/path/to/chrome'})
    @mock.patch('main.local_state_needs_patch', return_value=True)
    @mock.patch('main.get_last_version', return_value='150')
    @mock.patch('main.get_version_and_user_data_path', return_value={'stable': '/profile'})
    @mock.patch('main.parse_args', return_value=Namespace(
        country='us', yes=True,
        install_persistence=False, remove_persistence=False))
    def test_patch_failure_still_restarts_chrome(
            self, _parse_args, _paths, _version, _needs_patch,
            _shutdown, _patch, restart):
        with self.assertRaisesRegex(OSError, 'disk full'):
            main.main()

        restart.assert_called_once_with('/path/to/chrome')


if __name__ == '__main__':
    unittest.main()
