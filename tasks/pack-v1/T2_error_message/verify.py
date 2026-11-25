import unittest
from cli import request

class Acceptance(unittest.TestCase):
    def test_set_group_mentions_off(self):
        with self.assertRaises(ValueError) as ctx:
            request("set_group", "blue", lights=[1])
        msg = str(ctx.exception).lower()
        self.assertIn("off", msg)

    def test_set_unchanged(self):
        with self.assertRaises(ValueError) as ctx:
            request("set", "blue")
        msg = str(ctx.exception).lower()
        self.assertIn("white or red", msg)
        self.assertNotIn("off", msg)

if __name__ == "__main__":
    raise SystemExit(not unittest.main(exit=False).result.wasSuccessful())
