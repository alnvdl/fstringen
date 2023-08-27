import unittest

from .generator import gen


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


