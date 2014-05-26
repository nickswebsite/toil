import unittest

import core

class SettingsTests(unittest.TestCase):
    def test_strings_are_interpolated_properly(self):
        context = {
            "PROP_ONE": "value_one",
            "PROP_TWO": "value_two $PROP_ONE",
            "PROP_THREE": "value_three $PROP_TWO",
            "PROP_FOUR": [
                "$PROP_ONE list_item",
                "$PROP_TWO list_item"
            ],
            "PROP_FIVE": 5,
        }

        res = core.interpolate("$PROP_THREE", context)
        self.assertEqual("value_three value_two value_one", res)

        res = core.interpolate(["$PROP_ONE list_item", "$PROP_TWO list_item"], context)
        self.assertListEqual([
            "value_one list_item",
            "value_two value_one list_item",
        ], res)

        res = core.interpolate({
            "$PROP_ONE": "dictionary $PROP_FIVE",
        }, context)
        self.assertDictEqual({"value_one": "dictionary 5"}, res)

        res = core.interpolate(5, context)
        self.assertEqual(5, res)

if __name__ == "__main__":
    unittest.main()
