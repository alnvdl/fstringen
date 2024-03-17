import unittest

from .generator import gen
from .model import Model
from .model_test import test_model


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

        m = Model("test", test_model, refprefix="$")
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
