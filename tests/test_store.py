"""Store (persistent model/library store) contracts.

The store lives independently of install and update: downloaded content is
never deleted or re-downloaded when the version changes.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import store


class StoreLocationTests(unittest.TestCase):
    def test_store_lives_outside_the_program_folder(self):
        """The store must live outside the program folder; setup must not delete it."""
        with mock.patch("config.user_data_path",
                        side_effect=lambda *parts: str(Path("C:/data").joinpath(*parts))):
            resolved = store.store_dir()
        self.assertIn("store", str(resolved).lower())
        self.assertNotIn("program files", str(resolved).lower())

    def test_models_and_lib_have_separate_folders(self):
        self.assertNotEqual(store.models_dir(), store.lib_dir())
        self.assertTrue(store.models_dir().name == "models")
        self.assertTrue(store.lib_dir().name == "lib")

    def test_item_names_cannot_escape_the_store(self):
        for hostile in ("../../windows/system32", "..\\..\\evil", "a/b"):
            with self.assertRaises(store.StoreError):
                store._safe_name(hostile)

    def test_activate_appends_library_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch("store.store_dir", return_value=Path(tmp) / "store"):
                with mock.patch("store.lib_dir", return_value=Path(tmp) / "store" / "lib"), \
                     mock.patch("store.models_dir", return_value=Path(tmp) / "store" / "models"):
                    before = list(os.sys.path)
                    added = store.activate()
                    self.assertTrue(added)
                    for path in added:
                        self.assertIn(path, os.sys.path)
                    # Added paths go to the end: the bundled library wins.
                    self.assertGreater(os.sys.path.index(added[0]), len(before) - 1)
            for path in added:
                if path in os.sys.path:
                    os.sys.path.remove(path)


class StoreItemTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "store"
        patcher = mock.patch("store.store_dir", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def test_install_item_records_manifest_entry(self):
        source = Path(self._tmp.name) / "model.bin"
        source.write_bytes(b"model-bytes")
        record = store.install_item("Test Model", source, kind=store.KIND_MODEL,
                                    version="1.0")
        self.assertEqual(record["name"], "TestModel")
        self.assertEqual(record["version"], "1.0")
        self.assertEqual(record["size"], len(b"model-bytes"))
        self.assertTrue((self.root / "models" / "TestModel").exists())

        manifest = json.loads((self.root / "store.json").read_text(encoding="utf-8"))
        names = [i["name"] for i in manifest["items"]]
        self.assertIn("TestModel", names)

    def test_install_item_replaces_existing_content(self):
        source = Path(self._tmp.name) / "model.bin"
        source.write_bytes(b"v1")
        store.install_item("M", source, kind=store.KIND_MODEL)
        source.write_bytes(b"v2-longer")
        store.install_item("M", source, kind=store.KIND_MODEL)
        self.assertEqual((self.root / "models" / "M").read_bytes(), b"v2-longer")
        self.assertEqual(len(store.list_items()), 1)

    def test_install_item_rejects_missing_source(self):
        with self.assertRaises(store.StoreError):
            store.install_item("M", Path(self._tmp.name) / "missing.bin")

    def test_remove_item_deletes_content_and_manifest_entry(self):
        source = Path(self._tmp.name) / "model.bin"
        source.write_bytes(b"x")
        store.install_item("M", source, kind=store.KIND_MODEL)
        self.assertTrue(store.remove_item("M", kind=store.KIND_MODEL))
        self.assertFalse((self.root / "models" / "M").exists())
        self.assertEqual(store.list_items(), [])

    def test_corrupt_manifest_does_not_lose_files(self):
        source = Path(self._tmp.name) / "model.bin"
        source.write_bytes(b"x")
        store.install_item("M", source, kind=store.KIND_MODEL)
        (self.root / "store.json").write_text("{corrupt", encoding="utf-8")
        # A corrupt manifest is tolerated; the data files stay in place.
        self.assertEqual(store.list_items(), [])
        self.assertTrue((self.root / "models" / "M").exists())

    def test_summary_counts_models_and_libs(self):
        model = Path(self._tmp.name) / "m.bin"
        model.write_bytes(b"m")
        lib = Path(self._tmp.name) / "l.py"
        lib.write_bytes(b"l")
        store.install_item("M", model, kind=store.KIND_MODEL)
        store.install_item("L", lib, kind=store.KIND_LIB)
        summary = store.summary()
        self.assertEqual(summary["models"], 1)
        self.assertEqual(summary["libs"], 1)
        self.assertGreater(summary["size"], 0)


if __name__ == "__main__":
    unittest.main()
