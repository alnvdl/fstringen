import unittest

from .model import Model, ModelError


test_model = {
    "components": {
        "componentA": {
            "properties": {
                "name": "componentA",
                "color": "blue",
                "age": 3,
                "dead": False,
                "nothing": None,
                "nicknames": ["cA", "compA", "A"],
                "brokenref": "$/components/componentX"
            }
        },
        "componentB": {
            "favoriteprop": "$properties/color",
            "properties": {
                "name": "componentB",
                "color": "red",
                "age": 9,
                "dead": True,
                "nicknames": ["cB", "compB", "B"],
                "parent": "$/components/componentA"
            }
        }
    },
    "week": ["mon", "tue", "wed", "thu", "fri"],
    "animals": [
        {"type": "whale", "environment": "ocean", "other": "$/animals/1"},
        {"type": "lion", "environment": "land", "other": "$/animals/0"},
    ],
}


class TestModel(unittest.TestCase):
    def test_select_absolute(self):
        m = Model("test", test_model)
        # Sub-dict selection
        self.assertDictEqual(
            m.select("/components"), test_model["components"])
        self.assertEqual(
            m.select("/components").type, dict)

        # Two-level sub-dict selection
        self.assertEqual(
            m.select("/components/componentB"),
            (Model("componentB", test_model["components"]["componentB"])))

        # Leaf selection
        self.assertEqual(m.select("/components/componentB/properties/color"),
                         "red")
        self.assertEqual(
            m.select("/components/componentB/properties/color").type,
            str
        )
        self.assertEqual(m.select("/components/componentA/properties/nothing"),
                         None)
        self.assertEqual(
            m.select("/components/componentA/properties/nothing").type,
            type(None)
        )
        self.assertEqual(m.select("/week"), test_model["week"])
        self.assertEqual(m.select("/week").type, list)
        self.assertRaisesRegex(ModelError,
                               "Could not find path '/doesnotexist'.*",
                               m.select, "/doesnotexist")
        self.assertRaisesRegex(
            ModelError,
            "Could not find path '/components/componentX'.*", m.select,
            "/components/componentX")
        self.assertRaisesRegex(
            ModelError,
            "Could not find path '/components/componentB/properties/height'.*",
            m.select, "/components/componentB/properties/height")
        self.assertRaisesRegex(
            ModelError,
            "Cannot iterate over '/components/componentB/properties/dead'",
            m.select, "/components/componentB/properties/dead/*")
        self.assertRaisesRegex(
            ModelError,
            "Cannot lookup path 'type' in value 'True'",
            m.select, "/components/componentB/properties/dead/type")

    def test_select_star(self):
        m = Model("test", test_model)
        self.assertEqual(
            m.select("/components/*"),
            (test_model["components"]["componentA"],
             test_model["components"]["componentB"]))
        self.assertEqual(m.select("/components/*").name, "*")
        self.assertEqual(m.select("/components/*").type, tuple)
        # Models have extra attributes, check those.
        self.assertEqual(
            [el.name for el in m.select("/components/*")],
            ["componentA", "componentB"])
        self.assertEqual(
            [el.refprefix for el in m.select("/components/*")],
            [m.refprefix, m.refprefix])
        self.assertEqual(
            [el.root for el in m.select("/components/*")],
            [m, m])
        self.assertEqual(
            m.select("/components/*").select("/components/componentA"),
            test_model["components"]["componentA"])
        self.assertEqual(
            m.select("/components/*").select("1"),
            test_model["components"]["componentB"])

    def test_select_relative(self):
        m = Model("test", test_model)
        components = m.select("/components")
        compA = components.select("componentA")
        self.assertEqual(compA, test_model["components"]["componentA"])
        leaf = compA.select("properties/dead")
        self.assertEqual(leaf, False)

    def test_select_array(self):
        m = Model("test", test_model)
        self.assertEqual(
            m.select("/components/componentA/properties/nicknames"),
            test_model["components"]["componentA"]["properties"]["nicknames"])
        self.assertEqual(
            m.select("/components/componentA/properties/nicknames/0"), "cA")
        self.assertEqual(
            m.select("/components/componentA/properties/nicknames/1"), "compA")
        self.assertEqual(
            m.select("/components/componentA/properties/nicknames/2"), "A")
        self.assertRaisesRegex(
            ModelError, "Could not find path " +
            "'/components/componentA/properties/nicknames/3'.*", m.select,
            "/components/componentA/properties/nicknames/3")

        self.assertEqual(m.select("/week/0"), "mon")
        self.assertEqual(m.select("/week/2"), "wed")
        self.assertEqual(m.select("/week/-1"), "fri")
        self.assertRaisesRegex(ModelError,
                               "Enumerable navigation requires integers",
                               m.select, "/week/a")

        self.assertEqual(m.select("/animals"), test_model["animals"])
        self.assertEqual(m.select("/animals/*"), test_model["animals"])

        self.assertEqual(m.select("/animals/0"), test_model["animals"][0])
        self.assertEqual(m.select("/animals/1"), test_model["animals"][1])
        self.assertEqual(m.select("/animals/-1"), test_model["animals"][-1])

        self.assertEqual(m.select("/animals/0").select("type"), "whale")

        self.assertEqual(m.select("/animals/0/type"),
                         test_model["animals"][0]["type"])
        # Can select individual chars in strings.
        self.assertEqual(m.select("/animals/0/type/2"),
                         test_model["animals"][0]["type"][2])

        self.assertRaisesRegex(ModelError,
                               "Could not find path '/animals/99' in '.*'",
                               m.select, "/animals/99")

    def test_select_ref(self):
        m = Model("test", test_model, refprefix="$")
        self.assertEqual(m.select("/components/componentB/properties/parent"),
                         "$/components/componentA")

        # Go to ref as value.
        self.assertEqual(
            m.select("/components/componentB/properties/parent->"),
            test_model["components"]["componentA"])
        self.assertEqual(
            m.select("/components/componentB/properties/parent->" +
                     "/properties/color"),
            "blue")
        self.assertEqual(
            m.select("$/animals/1/other->/type"),
            "whale")

        # Go to ref.
        ref = m.select("/components/componentB/properties/parent") # noqa
        self.assertEqual(
            m.select(f"{ref}->"),
            test_model["components"]["componentA"])

        # Relative path seletion
        rref = m.select("/components/componentB/favoriteprop->")
        self.assertEqual(rref, "red")

        # Broken path selection
        self.assertRaisesRegex(
            ModelError,
            "Could not find path '/components/componentX'.*", m.select,
            "/components/componentA/properties/brokenref->")

    def test_select_default(self):
        m = Model("test", test_model)
        self.assertRaisesRegex(ModelError, "Could not find path .*",
                               m.select, "attr")
        self.assertEqual(m.select("attr", None), None)
        self.assertEqual(m.select("attr", "default value"), "default value")

        self.assertRaisesRegex(ModelError, "Could not find path .*",
                               m.select, "/components/componentZ")
        self.assertEqual(m.select("/components/componentZ", [1, 2]), [1, 2])

        self.assertRaisesRegex(ModelError, "Could not find path .*",
                               m.select, "/animals/99")
        self.assertEqual(m.select("/animals/99", "not found"), "not found")

        self.assertRaisesRegex(ModelError, "Could not find path .*",
                               m.select, "/animals/1/type/120")
        self.assertEqual(m.select("/animals/1/type/120", "x"), "x")

    def test_select_call(self):
        m = Model("test", test_model)
        self.assertRaisesRegex(ModelError, "Could not find path .*",
                               m, "attr")
        self.assertEqual(m("attr", "default value"), "default value")
