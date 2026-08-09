import unittest

from learning_agents import extract_json


class LLMJsonParserTests(unittest.TestCase):
    def test_repairs_missing_comma_in_model_object(self):
        parsed = extract_json('{"title":"第一周" "weeks":[{"week":1}]}')

        self.assertEqual(parsed["title"], "第一周")
        self.assertEqual(parsed["weeks"][0]["week"], 1)

    def test_rejects_non_object_root(self):
        with self.assertRaisesRegex(ValueError, "did not contain JSON"):
            extract_json('[1, 2, 3]')


if __name__ == "__main__":
    unittest.main()
