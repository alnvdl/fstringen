import inspect
import atexit
import json
import re
import textwrap

try:
    import yaml
except ImportError:
    yaml = None


def _putify(template):
    lines = template.split("\n")
    newlines = []
    for line in lines:
        # We don't care about indent in single-line strings
        if len(lines) == 1:
            indent = ''
        else:
            indent = line[:len(line) - len(line.lstrip())]
        # Take out all the isolated '{' and '}' characters
        line = line.replace("{{", "#_fstringen_ocbblock#").replace(
            "}}", "#_fstringen_ccbblock#")
        nl = line.replace("{", "{_put(").replace("}", ", '" + indent + "')}")
        # Put back all the isolated '{' and '}' characters
        nl = nl.replace("#_fstringen_ocbblock#",
                        "{{").replace("#_fstringen_ccbblock#", "}}")
        newlines.append(nl)
    return "\n".join(newlines)


def _put(obj, indent):
    if type(obj) in (list, tuple):
        newobj = [str(el).replace("\n", "\n" + indent) for el in obj]
        return ("\n" + indent).join(newobj)
    else:
        return str(obj).replace("\n", "\n" + indent)


def _fix_fstring(line):
    line = re.sub(r"(\"\"\"\*\s*)", "\"\"\"", line)
    line = re.sub(r"(\s*\*\"\"\")", "\"\"\"", line)
    return line


def _compile(fstringstar):
    globals_ = inspect.currentframe().f_back.f_globals
    locals_ = inspect.currentframe().f_back.f_locals

    fstring = "_fstringstar = f\"\"\"{}\"\"\"".format(_putify(fstringstar))

    exec(fstring, globals_, locals_)
    output = locals_["_fstringstar"]
    return output


def gen(model=None, fname=None, comment=None, notice=True):
    def realgen(fn):
        original_name = fn.__name__
        code = textwrap.dedent(inspect.getsource(fn))
        newcode = code[1:]  # Remove decorator
        newcode = re.sub(r"(f\"\"\"\*)", "_compile(\"\"\"", newcode)
        newcode = re.sub(r"(\*\"\"\")", "\"\"\")", newcode)

        # Re-execute function definition with the new code, in its own
        # globals/locals scope
        globals_ = inspect.currentframe().f_back.f_globals
        globals_["_put"] = _put
        globals_["_compile"] = _compile
        locals_ = inspect.currentframe().f_back.f_locals
        exec(newcode, globals_, locals_)
        newgen = locals_[original_name]

        def newfn(*args, **kwargs):
            r = newgen(*args, **kwargs)
            v = textwrap.dedent(r)
            if len(v) > 0 and v[0] == "\n":
                v = v[1:]
            if len(v) > 0 and v[-1] == "\n":
                v = v[:-1]
            return v

        if fname:
            if notice and not comment:
                raise FStringenError(
                    "Cannot place a notice without having the comment prefix")
            global _output
            _output[fname] = {
                "notice": notice,
                "comment": comment,
                "fn": newfn,
                "model": model
            }

        # Put the new function in globals, so others @gen code can call it
        # This is obviously dangerous, and it's one of the the reasons why
        # fstringen must not be used in anything else other than generators.
        globals_[original_name] = newfn

        return newfn

    return realgen


_output = {}


def _generate_all():
    for fname in _output:
        genopts = _output[fname]
        f = open(fname, "w")
        if genopts["notice"]:
            f.write(genopts["comment"] +
                    " File generated by fstringen. DO NOT EDIT.\n\n")
        fn = genopts["fn"]
        model = genopts["model"]
        f.write(fn(model))
        f.close()


atexit.register(_generate_all)


class FStringenError(Exception):
    pass


class FStringenNotFound(FStringenError):
    pass


class Mapper:
    def __init__(self, name, mappings):
        self.name = name
        self.mappings = mappings

    def __getitem__(self, key):
        return self.get(key)

    def get(self, key):
        return self.mappings.get(
            key, "<! MAPPING NOT FOUND IN '{}': {} !>".format(self.name, key))


class Model:
    def __init__(self, name, model, refindicator="#", root_model=None):
        self.name = name
        self.model = model
        self.refindicator = refindicator
        self.root_model = root_model
        if self.root_model is None:
            self.root_model = model

    @staticmethod
    def fromYAML(fname, refindicator="#", root_model=None):
        if yaml is None:
            raise FStringenError("Cannot find 'yaml' module")
        return Model(fname,
                     yaml.load(open(fname, "r").read(), Loader=yaml.Loader),
                     refindicator, root_model)

    @staticmethod
    def fromJSON(fname, refindicator="#", root_model=None):
        return Model(fname, json.loads(open(fname, "r").read()), refindicator,
                     root_model)

    @staticmethod
    def fromDict(dict_, name="dict", refindicator="#", root_model=None):
        return Model(name, dict_, refindicator, root_model)

    def __iter__(self):
        return iter(self.model)

    def __getitem__(self, key):
        if type(self.model) in (list, tuple):
            try:
                key = int(key)
            except ValueError:
                raise FStringenError(
                    "array model navigation requires integers")
        return self.model[key]

    def __str__(self):
        return str(self.model)

    def __repr__(self):
        return repr(self.model)

    def dict(self):
        return self.model

    def __eq__(self, other):
        return self.model == other.model and \
            self.name == other.name and \
            self.refindicator == other.refindicator and \
            self.root_model == other.root_model

    def has(self, path):
        callerctx = inspect.currentframe().f_back
        try:
            self.select(path, callerctx)
        except FStringenNotFound:
            return False

        return True

    def _new(self, name, submodel):
        return Model(name, submodel, self.refindicator, self.root_model)

    def select(self, path, callerctx=None):
        if callerctx is None:
            callerctx = inspect.currentframe().f_back

        # Root indicators (the initial /) are optional, since paths are always
        # relative to their ctx
        obj = self.model
        root = False
        if path.startswith(self.refindicator):
            path = path[1:]
        if path.startswith("/"):
            path = path[1:]
            obj = self.root_model
            root = True
        # Empty path trailings are ignored as well
        if path.endswith("/"):
            path = path[:-1]

        parts = path.split("/")
        curpath = []
        if root:
            curpath.append("")

        lastpart = None

        # TODO: we should probably browse models recursively instead of in a
        # loop
        for i in range(len(parts)):
            part = parts[i]

            match = re.match(r"\<([^<>]*)\>", part)
            if match is not None and match.lastindex == 1:
                var = match[1]
                if not var.isidentifier():
                    raise FStringenError(
                        "'{}' is not a valid Python identifier".format(var))
                if var in callerctx.f_locals:
                    part = str(callerctx.f_locals[var])
                    curpath.append("<{}>".format(part))
                else:
                    raise FStringenError(
                        "Could not find '{}' in local scope".format(var))
                if part.startswith(self.refindicator):
                    return self.select(part[1:], callerctx)
            else:
                curpath.append(part)

            if part == "*" and i == len(parts) - 1:
                if not hasattr(obj, "items"):
                    raise FStringenError("cannot iterate over '{}'".format(
                        "/".join(curpath[:-1])))
                return tuple(self._new(k, v) for k, v in obj.items())
            elif part.endswith("->"):
                part = part[:-2]
                newpath = obj[part]
                newmodel = self._new(part, obj)
                return newmodel.select(newpath, callerctx)
            else:
                if type(obj) in (list, tuple):
                    try:
                        part = int(part)
                    except ValueError:
                        raise FStringenError(
                            "array model navigation requires integers")
                try:
                    obj = obj[part]
                except (KeyError, IndexError):
                    raise FStringenNotFound(
                        "could not find path '{}' in model '{}'".format(
                            "/".join(curpath), obj))

            lastpart = part

        return self._new(lastpart, obj) if type(obj) in (list, tuple,
                                                         dict) else obj
