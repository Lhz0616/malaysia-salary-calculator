import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from services.update_checker import CURRENT_VERSION, parse_version
from services.update_downloader import UpdateDownloaderThread
from version import __version__


class TestVersionAndUpdateChecker(unittest.TestCase):

    def test_version_constants_match(self):
        """Ensure update_checker uses __version__ from version."""
        self.assertEqual(CURRENT_VERSION, __version__)
        self.assertIsInstance(__version__, str)
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+")

    def test_parse_version_equality(self):
        """Ensure identical versions with/without 'v' prefix compare as equal."""
        self.assertEqual(parse_version("0.1.0"), parse_version("v0.1.0"))
        self.assertEqual(parse_version("v0.1.1"), parse_version("0.1.1"))
        self.assertEqual(parse_version("V1.2.3"), parse_version("1.2.3"))

    def test_parse_version_ordering(self):
        """Ensure newer releases are recognized as strictly greater than current version."""
        self.assertGreater(parse_version("v0.1.1"), parse_version("v0.1.0"))
        self.assertGreater(parse_version("v1.0.0"), parse_version("v0.9.9"))
        self.assertGreater(parse_version("v0.2.0"), parse_version("v0.1.9"))
        self.assertFalse(parse_version("v0.1.0") > parse_version("0.1.0"))
        self.assertFalse(parse_version("v0.0.9") > parse_version("0.1.0"))

    def test_parse_version_with_prerelease(self):
        """Ensure pre-release suffix tags like -beta or -rc do not crash integer parsing."""
        self.assertEqual(parse_version("v0.1.1-beta.1"), (0, 1, 1))

    def test_update_downloader_instantiation(self):
        """Ensure UpdateDownloaderThread initializes properly."""
        downloader = UpdateDownloaderThread("https://example.com/installer.exe")
        self.assertEqual(downloader.download_url, "https://example.com/installer.exe")
        self.assertFalse(downloader._is_cancelled)
        downloader.cancel()
        self.assertTrue(downloader._is_cancelled)

