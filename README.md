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

A `Model` is simply a Python dictionary (which may be sourced from a YAML or
JSON file) representing a hierarchy, typically with deep nesting. The `select`
operation is run on `Model`s to select a sub-model based on a path selection
mechanism.

Generators are functions annotated with the `@gen()` decorator, which gives
some extra powers to f-strings expressions in them (automagic indentation,
smart list insertion and scope-related hacks). Generators may also be
configured to automatically output to files, with optional header notices.

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
generator. When the `model` and `fname` arguments are used, the generator
becomes a file generator, which is automatically executed and output to that
file when the script exists (i.e., you don't need to explicitly call any
generator).

Inside generators, fstringstars can use regular f-string `{expression}`
invocations.

The real power of fstringen comes with models, which allow easy selection of
model features:

- Every model has the `select` method, which takes a `path` and returns a new
  sub-model based on the query that path indicates.
- If a path ends with `/*` and the preceding path contains a dictionary,
  a list of sub-models is returned, containing all items in that dictionary.
  Every sub-model has a `name` attribute, corresponding to the dictionary key
  for that element.
- If a path element ends with `->`, the value contained in that attribute is
  assumed to contain a path (absolute or relative), and that path is used to
  look up the referenced object in the same model. The remainder of the path is
  used to continue the query on that object.
- If the select ends up in a leaf in the model, the value is returned (not a
  sub-model model).
- The `has` method in a model allows for verification of the existance of a
  path in the model.

It looks more complicated than it really is, but it's really easy to understand
once you start using!

So the two main imports from `fstringen` are `gen` and `Model`. An additional
import is available, `Mapper`, but it's entirely optional. It wraps a
dictionary for looking up things like type mappings, and it returns alarming
strings when no match is found.

## Caveats
fstringen does dangerous things with scope and function re-declaration. This
means you should only use it in scripts that are code generators, and code
generators alone (i.e., they don't do anything else). We sacrificed correctness
for neatness and ease-to-use.

Python 3.6+ is required. PyYAML is an optional dependency.
