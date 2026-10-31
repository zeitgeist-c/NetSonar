"""split_api_keys canonical behavior (config <-> GUI single source)."""
import unittest

from config import split_api_keys


class SplitApiKeysTest(unittest.TestCase):
    def test_list_dedup_and_strip(self):
        self.assertEqual(split_api_keys(["a", "b", "a", " "]), ["a", "b"])

    def test_string_separators(self):
        self.assertEqual(split_api_keys("a, b;c\nd"), ["a", "b", "c", "d"])

    def test_empty_inputs(self):
        self.assertEqual(split_api_keys(""), [])
        self.assertEqual(split_api_keys([]), [])
        self.assertEqual(split_api_keys(None), [])


if __name__ == "__main__":
    unittest.main()
