import unittest
from unittest.mock import patch, MagicMock
import launch_lan_macos as launcher

class MacLauncherTests(unittest.TestCase):
    def test_server_stops_when_dialog_closes(self):
        process=MagicMock();process.poll.return_value=None
        with patch.object(launcher,'address',return_value='192.168.1.20'), patch.object(launcher,'healthy',side_effect=[False,True]), patch.object(launcher.subprocess,'Popen',return_value=process), patch.object(launcher,'dialog') as dialog, patch.object(launcher.webbrowser,'open') as browser:
            launcher.main()
            process.terminate.assert_called_once()
            process.wait.assert_called_once_with(timeout=5)
            browser.assert_called_once_with('http://192.168.1.20:4174/')
            self.assertEqual(dialog.call_args.args[1],'Zastavit server')
    def test_existing_server_is_not_stopped(self):
        with patch.object(launcher,'address',return_value='192.168.1.20'), patch.object(launcher,'healthy',return_value=True), patch.object(launcher.subprocess,'Popen') as spawn, patch.object(launcher,'dialog'), patch.object(launcher.webbrowser,'open'):
            launcher.main();spawn.assert_not_called()
    def test_missing_network_is_reported(self):
        with patch.object(launcher,'address',side_effect=RuntimeError('No Wi-Fi')), patch.object(launcher,'dialog') as dialog:
            launcher.main();dialog.assert_called_once_with('No Wi-Fi')
