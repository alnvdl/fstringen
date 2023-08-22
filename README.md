# fstringen
fstringen (pronounced: f-string-gen) is a library for writing text and code
generators in Python. It builds upon [f-strings](
https://docs.python.org/3/reference/lexical_analysis.html#f-strings) available
in Python 3.6+, and it is based on two core concepts: models and generators.

fstringen was designed to generate code based on OpenAPI specs, but that is
just one possible use case. It can take any dictionary-equivalent model
(including YAML and JSON) and turn that into a browsable model, with
rudimentary support for cross-references. Generators then transform this model
in the desired output.

A `Model` is simply a Python dictionary (which may be manually iniatialized or
sourced from a YAML or JSON file) representing a hierarchy, typically with deep
nesting. The `select` operation is run on `Models`s to select a new sub-`Model`
based on a path selection mechanism.

Generators are functions annotated with the `@gen()` decorator, which gives
some extra powers to special f-strings expressions in them: automagic
indentation, smart list insertion and scope-related hacks. It makes your Python
code bear a vague resemblance to JSX code. Generators may also be configured to
automatically output to files, with optional header notices.

## Installing
You can install directly from PyPI:

    $ pip3 install fstringen --user

## Using
fstringen is based on special f-strings, called fstringstars: triple-quoted
f-strings that start and ends with an asterisk (`*`).

This special syntax indicates to fstringen that the string should be adapted
with extra features like automagic indentation, smart list insertion and
scope-escaping tricks.

A generator that outputs to a file looks like this (this is the `example.py`
file in this project):

```py
from fstringen import gen, Model

model = Model.fromDict({
    "structs": {
        "mystruct": {
            "color": "string"
        },
        "anotherstruct": {
            "name": "string",
            "age": "int"
        }
    }
})


@gen()
def gen_struct(struct):
    fields = ["{} {}".format(field.name, field)
              for field in struct.select("*")]

    return f"""*
    type {struct.name} struct {{
        {fields}
    }}

    *"""


@gen(model=model, fname="myfile.go", comment="//")
def gen_myfile(model):
    return f"""*
    package main

    // Let's generate some structs!
    {[gen_struct(struct) for struct in model.select("/structs/*")]}
    *"""
```

All generator functions using fstringstars must be decorated with `@gen()`.
When no parameters are passed to `gen()`, the generator is considerate a
subordinate generator (i.e., they need to be called explicitly from other
generators).

When the `model` and `fname` arguments are used, the generator becomes a file
generator, which is automatically executed and outputs to that file when the
Python interpreter exits (i.e., you don't need to explicitly call file
generators).

Inside generators, fstringstars can use regular f-string `{expression}`
invocations.

The real power of fstringen comes from `Model`s, which allow easy selection of
data:

- Every `Model` has the `select(path, [default])` method, which takes a `path`
  and returns a new `Model` based on the query that path indicates. Optionally,
  a `default` value can be passed to `select` for returning when `select' fails
  to find something.
- Calling a `Model` directly is a shorthand for `Model.select`. In other words,
  `myobj("/path")` is the same as `myobj.select("/path")`.
- Every `Model` has a `name` attribute, corresponding to the path element or
  array index through which we arrived at that element.
- If a path ends with `/*` and the preceding path contains a dictionary or
  enumerable value, a `Model` containing a list of `Model`s is returned,
  containing all items in that dictionary (as key, value) or enumerable (as
  index, value).
- If a path element ends with `->`, the value contained in that attribute is
  assumed to contain a path (absolute or relative), and that path is used to
  look up the referenced object in the same `Model`.
- Three convenience methods are also available in `Model`s. All of them can
  take a 'path' to query under that `Model`, of if called without a path, they
  apply to the `Model` in question:
  - `is_reference(path)` checks whether a given `Model` contains a reference.
  - `has(path)` allows for verification of the existence of a path under that
    `Model`.
  - `is_enabled(path)` method verifies that the path exists and has a truthy
    value.

The two most commonly used imports from `fstringen` are `gen` and `Model`.

Fstringstars have one important distiction when compared to regular
triple-quoted strings: their first and last `\n` are discarded when present.
Therefore, the following are all equivalent:

    fstringstar = f"""*
    ...
    *"""

    fstringstar = f"""*...*"""

    fstringstar = f"""*
    ...*"""

    fstringstar = f"""*...
    *"""

This design intentional, especially because it enables the first style shown
above (newline at the start, newline at the end), which makes generators more
readable. Avoid using regular triple-quoted strings in generators to keep
behavior more preditable and consistent.

Also, please note that using single-quotes to define fstringstars is not
supported (i.e., `f'''*...*'''` is not a valid fstringstar).

## Caveats
fstringen does dangerous things with scope and function re-declaration. This
means you should only use it in scripts that are code generators, and code
generators alone (i.e., they don't do anything else). We sacrificed correctness
for neatness and ease-to-use.

Since fstringen tramples over all common sense, pretty much all exceptions are
intercepted and transformed into custom error messages. Otherwise, because of
the scope tricks and function re-declarations, most tracebacks and error
messages become useless and confusing.

Python 3.6+ is required. PyYAML is an optional dependency.

## Known issues
Because of Python limitations, a few things are not possible:

**Quotes in fstringstars strings**

Just as you can't have a triple-quoted string that starts or ends with quotes
in Python:

    my_str = """"a""""

You can't have a fstringstar like this:

    my_fstringstar = f"""*"a"*"""

That's because Python can't figure out how that string starts or ends
(fstringstars are compiled to triple-quoted Python f-strings). You can achieve
the same result by escaping quotes with `//` when they start or end a string:

    my_fstringstar = f"""*\\"a\\"*"""

**Don't compare with `is` and avoid `isinstance`**

When dealing with a `Model`, don't use the `is` comparison operator. Consider
the following code:

    mybool = model.select("/path/to/a/bool")

When checking whether `mybool` is `True` or `False`, do it using `==` or if in
a conditional, just check the value directly without a comparison
(`if mybool`). The same applies to `None`.

The reason for this limitation is that `select` always returns a `Model`, and a
`Model` can never be compared to Python objects using the `is` operator, which
verifies that two expressions point to the same object.
However, equality operators (`==` and `!=`) work just fine because `Model`
applies some magic to make that work.

Because `NoneType` and `bool` cannot be subclassed in Python, a `Model` isn't
able to inherit from those (as it does for `int`, `str`, `list`, `dict`, etc.).
For that reason, you should also avoid using `isinstance`. Instead, you can
verify the original type for a value by checking the `type` attribute in a
`Model`.

**Variable scoping in list comprehensions**

List comprehensions have their own frame and local scope in Python 3+, and the
scope-escaping tricks fstringen uses don't work in them.

So if you have code like this:

    myvar = "myvalue"

    return f"""*
    ...

    {[do_something(entity, myvar) for entity in model.select("/entities/*")]}
    *"""

It will not work, because `myvar` will not be accesible to that list
comprehension. To work around this, you can either have the list comprehension
outside the fstringstar, or directly embed the variable's value in the list
comprehension expression.
