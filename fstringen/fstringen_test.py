import unittest
from fstringen import gen, Model, SelectableError

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
        m = Model.fromDict(test_model)
        # Sub-dict selection
        self.assertDictEqual(
            m.select("/components"), test_model["components"])
        self.assertEqual(
            m.select("/components").type, dict)

        # Two-level sub-dict selection
        self.assertEqual(
            m.select("/components/componentB"),
            (Model.fromDict(test_model["components"]["componentB"],
                            name="componentB",
                            root=test_model)))

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
        self.assertRaisesRegex(SelectableError,
                               "Could not find path '/doesnotexist'.*",
                               m.select, "/doesnotexist")
        self.assertRaisesRegex(
            SelectableError,
            "Could not find path '/components/componentX'.*", m.select,
            "/components/componentX")
        self.assertRaisesRegex(
            SelectableError,
            "Could not find path '/components/componentB/properties/height'.*",
            m.select, "/components/componentB/properties/height")
        self.assertRaisesRegex(
            SelectableError,
            "Cannot iterate over '/components/componentB/properties/dead'",
            m.select, "/components/componentB/properties/dead/*")
        self.assertRaisesRegex(
            SelectableError,
            "Cannot lookup path 'type' in value 'True'",
            m.select, "/components/componentB/properties/dead/type")

    def test_select_star(self):
        m = Model.fromDict(test_model)
        self.assertEqual(
            m.select("/components/*"),
            (test_model["components"]["componentA"],
             test_model["components"]["componentB"]))
        self.assertEqual(m.select("/components/*").name, "*")
        self.assertEqual(m.select("/components/*").type, tuple)
        # Selectables have extra attributes, check those
        self.assertEqual(
            [el.name for el in m.select("/components/*")],
            ["componentA", "componentB"])
        self.assertEqual(
            [el.refindicator for el in m.select("/components/*")],
            [m.refindicator, m.refindicator])
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
        m = Model.fromDict(test_model)
        components = m.select("/components")
        compA = components.select("componentA")
        self.assertEqual(compA, test_model["components"]["componentA"])
        leaf = compA.select("properties/dead")
        self.assertEqual(leaf, False)

    def test_select_array(self):
        m = Model.fromDict(test_model)
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
            SelectableError, "Could not find path " +
            "'/components/componentA/properties/nicknames/3'.*", m.select,
            "/components/componentA/properties/nicknames/3")

        self.assertEqual(m.select("/week/0"), "mon")
        self.assertEqual(m.select("/week/2"), "wed")
        self.assertEqual(m.select("/week/-1"), "fri")
        self.assertRaisesRegex(SelectableError,
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

        self.assertRaisesRegex(SelectableError,
                               "Could not find path '/animals/99' in '.*'",
                               m.select, "/animals/99")

    def test_select_ref(self):
        m = Model.fromDict(test_model, refindicator="$")
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
            SelectableError,
            "Could not find path '/components/componentX'.*", m.select,
            "/components/componentA/properties/brokenref->")

    def test_select_default(self):
        m = Model.fromDict(test_model)
        self.assertRaisesRegex(SelectableError, "Could not find path .*",
                               m.select, "attr")
        self.assertEqual(m.select("attr", "default value"), "default value")

        self.assertRaisesRegex(SelectableError, "Could not find path .*",
                               m.select, "/components/componentZ")
        self.assertEqual(m.select("/components/componentZ", [1, 2]), [1, 2])

        self.assertRaisesRegex(SelectableError, "Could not find path .*",
                               m.select, "/animals/99")
        self.assertEqual(m.select("/animals/99", "not found"), "not found")

        self.assertRaisesRegex(SelectableError, "Could not find path .*",
                               m.select, "/animals/1/type/120")
        self.assertEqual(m.select("/animals/1/type/120", "x"), "x")

    def test_select_call(self):
        m = Model.fromDict(test_model)
        self.assertRaisesRegex(SelectableError, "Could not find path .*",
                               m, "attr")
        self.assertEqual(m("attr", "default value"), "default value")


class TestGen(unittest.TestCase):
    def test_simple(self):
        @gen()
        def fn():
            a = 1
            return f"""*
            {a}
            *"""

        self.assertEqual(fn(), "1")

        @gen()
        def fn2():
            a = 1
            return f"""*
            x
              {a}
            *"""

        self.assertEqual(fn2(), "x\n  1")

        @gen()
        def fn2():
            a = 1
            b = "something"
            c = "."

            return f"""*
            x
              {a}
            {b}
               {c}
            *"""

        self.assertEqual(fn2(), "x\n  1\nsomething\n   .")

    def test_basic_newline_equivalence(self):
        @gen()
        def fn1():
            return f"""*
            ...
            *""" # noqa

        @gen()
        def fn2():
            return f"""*...*""" # noqa

        @gen()
        def fn3():
            return f"""*
            ...*""" # noqa

        @gen()
        def fn4():
            return f"""*...
            *""" # noqa

        self.assertEqual(fn1(), "...")
        self.assertEqual(fn2(), "...")
        self.assertEqual(fn3(), "...")
        self.assertEqual(fn4(), "...")

    def test_quotes(self):
        @gen()
        def fn():
            a = 1
            return f"""*
            \\"{a}\\"
            *"""
        self.assertEqual(fn(), "\"1\"")

        @gen()
        def fn2():
            a = 1
            return f"""*\\"{a}\\*"""
        self.assertEqual(fn(), "\"1\"")

    def test_blank_lines(self):
        @gen()
        def fn():
            a = 1
            return f"""*

            {a}
            *"""

        self.assertEqual(fn(), "\n1")

        @gen()
        def fn2():
            a = 1
            return f"""*

            {a}

            *"""

        self.assertEqual(fn2(), "\n1\n")

        @gen()
        def fn2():
            a = 1
            return f"""*

            x:
              {a}


            *"""

        self.assertEqual(fn2(), "\nx:\n  1\n\n")

    def test_list(self):
        @gen()
        def fn():
            elements = [1, 2]
            return f"""*
            {elements}
            *"""

        self.assertEqual(fn(), "1\n2")

        @gen()
        def fn():
            elements = [1, 2]
            return f"""*
            x
              {elements}
            *"""

        self.assertEqual(fn(), "x\n  1\n  2")

    def test_single_line(self):
        @gen()
        def fn():
            a = "y\nx"
            return f"""*    {a}  *"""

        self.assertEqual(fn(), "    y\nx  ")

        @gen()
        def fn2():
            a = [1, 2]
            return f"""*{a}*"""

        self.assertEqual(fn2(), "1\n2")

    def test_indent(self):
        @gen()
        def multiline_string():
            return f"""*
            multiline
              string
            *""" # noqa

        # Indentation-level of outside code shouldn't interfere
        @gen()
        def fn(cond):
            a = [1, 2]
            if cond:
                return f"""*
                {a}
                *"""
            return f"""*
            {a}
            *"""
        self.assertEqual(fn(False), "1\n2")
        self.assertEqual(fn(True), "1\n2")

        # Multi-line strings should be dedented
        @gen()
        def fn2():
            a = [multiline_string(), multiline_string()]
            return f"""*
            {a}
            *"""
        self.assertEqual(fn2(), "multiline\n  string\nmultiline\n  string")

    def test_dict(self):
        @gen()
        def fn():
            a = {"x": 1}
            return f"""*
            dict: {a}
            *"""

        self.assertEqual(fn(), "dict: {'x': 1}")

    def test_return_none(self):
        @gen()
        def fn_none():
            return

        @gen()
        def fn():
            a = "2" # noqa
            l = [1, None, 2] # noqa
            return f"""*
            a: 2{fn_none()}
            {l}
            {fn_none()}
            b
            *"""

        # When None is part of a list, it should be hidden
        # When None is a direct value, it shows as ""
        self.assertEqual(fn(), "a: 2\n1\n2\n\nb")

    def test_call(self):
        @gen()
        def abc():
            return "abc"

        @gen()
        def fn():
            a = {"x": 1}
            return f"""*
            dict: {a}
            *"""

        @gen()
        def fn2():
            return f"""*
            {abc()} call:
                {fn()}
            *"""

        self.assertEqual(fn2(), "abc call:\n    dict: {'x': 1}")


class TestIntegration(unittest.TestCase):
    # TODO: test file generation

    def test_gen_select(self):
        @gen()
        def gen_color(component):
            return f"""*
            color: {component.select("properties/color")}
            *"""

        @gen()
        def gen_component(component):
            parent = None
            if component.has("properties/parent"):
                parent = component.select("properties/parent->").name
                parent = f"parent: {parent}"

            return f"""*
            # Component {component.select("properties/name")}:
              {parent}
              {gen_color(component)}
              nicknames:
                {["- " + x for x in component.select("properties/nicknames")]}

            *"""

        @gen()
        def gen_all(model):
            components = [
                gen_component(component)
                for component in model.select("/components/*")
            ]

            return f"""*
            {components}
            *"""

        m = Model.fromDict(test_model, refindicator="$")
        self.assertEqual(
            gen_all(m), """# Component componentA:

  color: blue
  nicknames:
    - cA
    - compA
    - A

# Component componentB:
  parent: componentA
  color: red
  nicknames:
    - cB
    - compB
    - B
""")
