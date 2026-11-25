import unittest

from cli import request


class ExistingTests(unittest.TestCase):
    def test_set_white(self):
        self.assertEqual(request("set", "white")["ok"], True)


if __name__ == "__main__":
    unittest.main()
