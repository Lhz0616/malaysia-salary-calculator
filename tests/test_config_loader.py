import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from core.config_loader import (
    _resolve_data_dir,
    get_config,
    get_configs,
    get_resource_path,
    load_all_configs,
    save_all_config,
)


class TestConfigLoader(unittest.TestCase):

    def test_get_resource_path_dev_environment(self):
        """Verify resource path resolution works cleanly in normal development mode."""
        dark_qss = get_resource_path("assets/styles/dark.qss")
        self.assertTrue(os.path.isfile(dark_qss), f"Expected dark.qss to exist at {dark_qss}")

        dark_qss_src = get_resource_path("src/assets/styles/dark.qss")
        self.assertTrue(os.path.isfile(dark_qss_src), f"Expected dark.qss (src-prefixed) to exist at {dark_qss_src}")

        icon_path = get_resource_path("icon/app_icon.ico")
        self.assertTrue(os.path.isfile(icon_path), f"Expected app_icon.ico to exist at {icon_path}")

        assets_dir = get_resource_path("assets")
        self.assertTrue(os.path.isdir(assets_dir), f"Expected assets dir to exist at {assets_dir}")

    def test_get_resource_path_pyinstaller_meipass(self):
        """Verify resource path resolution when running under PyInstaller (sys._MEIPASS)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            meipass_dir = os.path.join(tmp_dir, "_MEIPASS_mock")
            styles_dir = os.path.join(meipass_dir, "assets", "styles")
            os.makedirs(styles_dir, exist_ok=True)
            icon_dir = os.path.join(meipass_dir, "icon")
            os.makedirs(icon_dir, exist_ok=True)

            dummy_qss = os.path.join(styles_dir, "dark.qss")
            with open(dummy_qss, "w", encoding="utf-8") as f:
                f.write("/* mock dark qss */")

            dummy_ico = os.path.join(icon_dir, "app_icon.ico")
            with open(dummy_ico, "wb") as f:
                f.write(b"ico-data")

            with patch.object(sys, "_MEIPASS", meipass_dir, create=True):
                # Should resolve both bare and src-prefixed paths directly from _MEIPASS
                res_qss = get_resource_path("assets/styles/dark.qss")
                self.assertEqual(os.path.abspath(res_qss), os.path.abspath(dummy_qss))

                res_qss_src = get_resource_path("src/assets/styles/dark.qss")
                self.assertEqual(os.path.abspath(res_qss_src), os.path.abspath(dummy_qss))

                res_ico = get_resource_path("icon/app_icon.ico")
                self.assertEqual(os.path.abspath(res_ico), os.path.abspath(dummy_ico))

                res_assets = get_resource_path("assets")
                self.assertEqual(os.path.abspath(res_assets), os.path.abspath(os.path.join(meipass_dir, "assets")))

    def test_resolve_data_dir_external_priority(self):
        """External .data directory next to the executable must take priority over bundled/dev data."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_exe_dir = os.path.join(tmp_dir, "app_install_dir")
            external_data = os.path.join(fake_exe_dir, ".data")
            os.makedirs(external_data, exist_ok=True)
            custom_cfg = os.path.join(external_data, "config.json")
            with open(custom_cfg, "w", encoding="utf-8") as f:
                json.dump({"custom": True}, f)

            fake_exe = os.path.join(fake_exe_dir, "MalaysianSalaryCalculator.exe")

            with patch.object(sys, "argv", [fake_exe]):
                resolved = _resolve_data_dir()
                self.assertEqual(os.path.abspath(resolved), os.path.abspath(external_data))

    def test_resolve_data_dir_bundled_fallback(self):
        """If no external directory exists, resolve_data_dir falls back to bundled data."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            meipass_dir = os.path.join(tmp_dir, "_MEIPASS_mock")
            bundled_data = os.path.join(meipass_dir, "data")
            os.makedirs(bundled_data, exist_ok=True)
            with open(os.path.join(bundled_data, "config.json"), "w", encoding="utf-8") as f:
                json.dump({"bundled": True}, f)

            empty_exe_dir = os.path.join(tmp_dir, "empty_dir")
            os.makedirs(empty_exe_dir, exist_ok=True)
            fake_exe = os.path.join(empty_exe_dir, "MalaysianSalaryCalculator.exe")

            with patch.object(sys, "argv", [fake_exe]):
                with patch.object(sys, "_MEIPASS", meipass_dir, create=True):
                    resolved = _resolve_data_dir()
                    self.assertEqual(os.path.abspath(resolved), os.path.abspath(bundled_data))

    def test_save_all_config_creates_directory(self):
        """save_all_config should automatically create target directory if missing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            target_dir = os.path.join(tmp_dir, "new_data_folder")
            self.assertFalse(os.path.exists(target_dir))

            with patch("core.config_loader._resolve_data_dir", return_value=target_dir):
                test_payload = {"test_config": {"key": "value"}}
                save_all_config(test_payload)

                self.assertTrue(os.path.isdir(target_dir))
                saved_file = os.path.join(target_dir, "test_config.json")
                self.assertTrue(os.path.isfile(saved_file))
                with open(saved_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.assertEqual(data, {"key": "value"})


if __name__ == "__main__":
    unittest.main()
