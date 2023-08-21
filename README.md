# fstringen
fstringen (pronounced: f-string-gen) is a library for writing text and code
generators in Python. It builds upon [f-strings](
https://docs.python.org/3/reference/lexical_analysis.html#f-strings) available
in Python 3.6+, and it is based on two core concepts: models and generators.

fstringen was designed to generate code based on OpenAPI specs, but that's
just one possible use case. It can take any dictionary-equivalent model
(including YAML and JSON) and turn that into a browsable model, with
rudimentary support for cross-references. Generators then transform this model
in the desired output.

A `Selectable` is simply a Python dictionary (which may be sourced from a YAML
or JSON file) representing a hierarchy, typically with deep nesting. The
`select` operation is run on `Selectable`s to select a new `Selectable` based
on a path selection mechanism. `Model` is just an alias for `Selectable`, and
it's usually used when referring to a `Selectable` loaded from a file

Generators are functions annotated with the `@gen()` decorator, which gives
some extra powers to special f-strings expressions in them (automagic
indentation, smart list insertion and scope-related hacks). Generators may also
be configured to automatically output to files, with optional header notices.

## Installing
You can install directly from PyPI:

    $ pip3 install fstringen --user

## Using
fstringen is based on special f-strings, called fstringstars. They are
basically triple-quoted f-strings that start and ends with an asterisk (`*`).
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
When no parameters are given, the generator is considerate a subordinate
generator (i.e., they need to be called explicitly from other generators).
When the `model` and `fname` arguments are used, the generator becomes a file
generator, which is automatically executed and output to that file when the
script exists (i.e., you don't need to explicitly call file generators).

Inside generators, fstringstars can use regular f-string `{expression}`
invocations.

The real power of fstringen comes with `Selectable`s and `Model`s, which allow
easy selection of data (`Model` is just an alias for `Selectable`, and `Model`
is usually used when referring to a `Selectable` loaded from a file):

- Every `Selectable` has the `select` method, which takes a `path` and returns
  a new `Selectable` based on the query that path indicates. Optionally, a
  `default` value can be passed to `select` for returning when select fails to
  find something.
- Calling a `Selectable` is a shorthand for `Selectable.select`. In other
  words, `myobj("/path")` is the same as `myobj.select("/path")`.
- Every `Selectable` has a `name` attribute, corresponding to the dictionary
  key or array index for that element.
- If a path ends with `/*` and the preceding path contains a dictionary or
  enumerable value, a `Selectable` list of `Selectable`s is returned,
  containing all items in that dictionary (as key, value) or enumerable (as
  index, value).
- If a path element ends with `->`, the value contained in that attribute is
  assumed to contain a path (absolute or relative), and that path is used to
  look up the referenced object in the same `Model`.
- Three convenience methods are also available in `Selectable`s. All of them
  can take a path to query under that `Selectable`, of if called without a
  path, they apply to the `Selectable` in question:
  - `is_reference` checks whether a given `Selectable` contains a reference.
  - `has` allows for verification of the existence of a path under that
    `Selectable`.
  - `is_enabled` method verifies that the path exists and has a truthy value.

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
(fstringstars are compiled to triple-quoted Python f-strings). You achieve the
same result by escaping quotes with `//` when they start or end a string:

    my_fstringstar = f"""*\\"a\\"*"""

**Don't compare with `is` and avoid `isinstance`**

When dealing with a `Selectable` or a `Model`, don't use the `is` comparison
operator. Consider the following code:

    mybool = model.select("/path/to/a/bool")

When checking whether `mybool` is `True` or `False`, do it using `==` or if in
a conditional, just check the value directly without a comparison
(`if mybool`). The same applies to `None`.

The reason for this limitation is that `select` always returns a `Selectable`,
and a `Selectable` can never be compared to Python objects using the `is`
operator, which verifies that two expressions point to the same object.
However, equality operators (`==` and `!=`) work just fine because `Selectable`
applies some magic.

Because `NoneType` and `bool` cannot be subclassed in Python, a `Selectable`
isn't able to inherit from those (as it does for `int`, `str`, `list`, `dict`,
etc.). For that reason, you should also avoid using `isinstance`. Instead, you
can verify the original type for a value by checking the `type` attribute in a
`Selectable`.

**Variable scoping in list comprehensions**

List comprehensions have their own frame and local scope in Python 3+, and the
scope-escaping tricks fstringen uses don't work in them.

So if you have code like this:

    myvar = "myvalue"

    return f"""*
    ...

    {[do_something(entity, myvar) for entity in model.select("/entities/*")]}
    *"""

It will not work, because myvar will not be accesible to that list
comprehension. To work around this, you can either have the list comprehension
ouside the fstringstar, or directly embed the variable's value in the list
comprehension expression.
