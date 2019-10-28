import unittest
from fstringen import gen, Model, FStringenError, FStringenNotFound

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
    "week": ["mon", "tue", "wed", "thu", "fri"]
}


class TestModel(unittest.TestCase):
    def test_select_absolute(self):
        # Sub-dict selection
        m = Model.fromDict(test_model)
        self.assertDictEqual(
            m.select("/components"), test_model["components"])

        # * selection
        self.assertEqual(
            m.select("/components/*"),
            (test_model["components"]["componentA"],
             test_model["components"]["componentB"]))
        self.assertEqual(m.select("/components/*").name, "*")
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

        # Two-level sub-dict selection
        self.assertEqual(
            m.select("/components/componentB"),
            (Model.fromDict(test_model["components"]["componentB"],
                            name="componentB",
                            root=test_model)))

        # Leaf selection
        self.assertEqual(m.select("/components/componentB/properties/color"),
                         "red")
        self.assertEqual(m.select("/components/componentA/properties/nothing"),
                         None)
        self.assertEqual(m.select("/week"), test_model["week"])
        self.assertRaisesRegex(FStringenNotFound,
                               "could not find path '/doesnotexist'.*",
                               m.select, "/doesnotexist")
        self.assertRaisesRegex(
            FStringenNotFound,
            "could not find path '/components/componentX'.*", m.select,
            "/components/componentX")
        self.assertRaisesRegex(
            FStringenNotFound,
            "could not find path '/components/componentB/properties/height'.*",
            m.select, "/components/componentB/properties/height")
        self.assertRaisesRegex(
            FStringenError,
            "cannot iterate over '/components/componentB/properties/color'",
            m.select, "/components/componentB/properties/color/*")

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
            FStringenNotFound, "could not find path " +
            "'/components/componentA/properties/nicknames/3'.*", m.select,
            "/components/componentA/properties/nicknames/3")

        self.assertEqual(m.select("/week/0"), "mon")
        self.assertEqual(m.select("/week/2"), "wed")
        self.assertEqual(m.select("/week/-1"), "fri")
        self.assertRaisesRegex(FStringenError,
                               "array navigation requires integers",
                               m.select, "/week/a")

    def test_select_ref(self):
        m = Model.fromDict(test_model, refindicator="$")
        self.assertEqual(m.select("/components/componentB/properties/parent"),
                         "$/components/componentA")
        self.assertEqual(
            m.select("/components/componentB/properties/parent->"),
            test_model["components"]["componentA"])
        ref = m.select("/components/componentB/properties/parent") # noqa
        self.assertEqual(
            m.select("<ref>->"),
            test_model["components"]["componentA"])
        # Relative path seletion
        rref = m.select("/components/componentB/favoriteprop->")
        self.assertEqual(rref, "red")
        # Broken path selection
        self.assertRaisesRegex(
            FStringenNotFound,
            "could not find path '/components/componentX'.*", m.select,
            "/components/componentA/properties/brokenref->")

    def test_select_replace(self):
        comp = "componentA" # noqa
        prop = "color" # noqa
        m = Model.fromDict(test_model)
        self.assertEqual(m.select("/components/<comp>/properties/<prop>"),
                         "blue")
        # We cannot use assertRaisesRegex because of the scope trickery in
        # select with paths containing <...>
        try:
            m.select("/components/<comp>/properties/<fail>")
        except FStringenError as e:
            self.assertEqual(str(e), "Could not find 'fail' in local scope")
        else:
            raise Exception("test_select_replace_failed")


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
            parent = ""
            if component.has("properties/parent"):
                parent = component.select("properties/parent->").name
                parent = f"parent: {parent}"

            return f"""*
            # Component {component.select("properties/name")}:
              {gen_color(component)}
              nicknames:
                {["- " + x for x in component.select("properties/nicknames")]}
              {parent}
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
  color: red
  nicknames:
    - cB
    - compB
    - B
  parent: componentA""")
