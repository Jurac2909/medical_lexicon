import os
import tempfile
import unittest
from pathlib import Path

from app import paths


class EnvTestCase(unittest.TestCase):
    """Base class that restores the environment after each test."""

    VARIABLES = ("MEDLEX_DATA_DIR", "SNAP_USER_COMMON", "SNAP_COMMON", "HF_HOME")

    def setUp(self):
        self._saved = {name: os.environ.get(name) for name in self.VARIABLES}
        for name in self.VARIABLES:
            os.environ.pop(name, None)
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        for name, value in self._saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        self._tmp.cleanup()


class TestDataDir(EnvTestCase):
    def test_defaults_to_project_directory(self):
        self.assertEqual(paths.data_dir(), paths.PROJECT_ROOT)

    def test_explicit_variable_wins(self):
        os.environ["MEDLEX_DATA_DIR"] = str(self.tmp / "explicit")
        os.environ["SNAP_USER_COMMON"] = str(self.tmp / "snap-user")
        self.assertEqual(paths.data_dir(), self.tmp / "explicit")

    def test_snap_user_common_preferred_over_snap_common(self):
        os.environ["SNAP_USER_COMMON"] = str(self.tmp / "snap-user")
        os.environ["SNAP_COMMON"] = str(self.tmp / "snap-system")
        self.assertEqual(paths.data_dir(), self.tmp / "snap-user")

    def test_snap_common_used_for_daemons(self):
        os.environ["SNAP_COMMON"] = str(self.tmp / "snap-system")
        self.assertEqual(paths.data_dir(), self.tmp / "snap-system")

    def test_directory_is_created(self):
        target = self.tmp / "nested" / "data"
        os.environ["MEDLEX_DATA_DIR"] = str(target)
        self.assertTrue(paths.data_dir().is_dir())

    def test_read_only_location_falls_back_to_temp(self):
        # Simulate the read-only $SNAP: mkdir raises, the app must not crash.
        original_mkdir = Path.mkdir
        calls = []

        def failing_mkdir(self, *args, **kwargs):
            if "denied" in str(self):
                calls.append(self)
                raise PermissionError("read-only file system")
            return original_mkdir(self, *args, **kwargs)

        os.environ["MEDLEX_DATA_DIR"] = str(self.tmp / "denied")
        Path.mkdir = failing_mkdir
        try:
            result = paths.data_dir()
        finally:
            Path.mkdir = original_mkdir

        self.assertTrue(calls, "the denied path should have been attempted")
        self.assertTrue(result.is_dir())
        self.assertNotIn("denied", str(result))


class TestDerivedDirs(EnvTestCase):
    def test_export_dir_is_inside_data_dir(self):
        os.environ["MEDLEX_DATA_DIR"] = str(self.tmp)
        self.assertEqual(paths.export_dir(), self.tmp / "exports")
        self.assertTrue(paths.export_dir().is_dir())

    def test_model_cache_follows_hf_home(self):
        os.environ["HF_HOME"] = str(self.tmp / "hf")
        self.assertEqual(paths.model_cache_dir(), self.tmp / "hf")

    def test_model_cache_defaults_below_data_dir(self):
        os.environ["MEDLEX_DATA_DIR"] = str(self.tmp)
        self.assertEqual(paths.model_cache_dir(), self.tmp / "hf-cache")


if __name__ == "__main__":
    unittest.main()
