import atexit
import inspect
import json
import re
import sys
import textwrap
import traceback

try:
    import yaml
except ImportError:
    yaml = None


def _putify(template):
    if "\n" in template:
        template = textwrap.dedent(template)

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
    if isinstance(obj, list) or isinstance(obj, tuple):
        newobj = [str(el).replace("\n", "\n" + indent)
                  for el in obj if el is not None]
        return ("\n" + indent).join(newobj)
    else:
        if obj is None:
            return ""
        return str(obj).replace("\n", "\n" + indent)


def _errmsg(exc_info, fnname, code=None, fstringstar=None):
    excl = exc_info[0]
    exc = exc_info[1]
    tb = exc_info[2]

    lineno = traceback.extract_tb(tb)[-1][1] - 1
    # If we have precise line information, use it
    line = traceback.extract_tb(tb)[-1][3]
    if line:
        subfn = traceback.extract_tb(tb)[-1][2]
        return f"""
Error in function '{subfn}' called by generator '{fnname}':
{"-"*80}
Line {lineno + 1}: {line} <- \033[91m{excl.__name__}: {str(exc)}\033[0m
{"-"*80}
"""



    if code is not None:
        fnlines = code.split("\n")
        startline = max(lineno - 3, 0)
        endline = min(lineno + 3, len(fnlines) - 1)
        try:
            fnlines[lineno] = (fnlines[lineno] +
                            f"\033[91m <- {type(exc).__name__}: " +
                            f"{str(exc)}\033[0m")
            msg = "\n".join(fnlines[startline:endline])
            if endline < len(fnlines) - 1:
                msg += "\n[...]"
        except IndexError:
            msg = "Could not determine source location"

        return f"""
Error in generator '{fnname}':
{"-"*80}
{textwrap.dedent(msg)}
{"-"*80}
"""

    if fstringstar is not None:
        return f"""
Error in fstringstar in generator '{fnname}':
{"-"*80}
fstringstar: f\"\"\"*
{textwrap.dedent(fstringstar).strip()}
*\"\"\" <- \033[91m{excl.__name__}: {str(exc)}\033[0m
{"-"*80}
"""


def _compile(fstringstar):
    gen_frame = inspect.currentframe().f_back
    globals_ = gen_frame.f_globals
    locals_ = gen_frame.f_locals

    fstring = "_fstringstar = f\"\"\"{}\"\"\"".format(_putify(fstringstar))
    try:
        exec(fstring, globals_, locals_)
    except Exception:
        fnname = gen_frame.f_code.co_name
        msg = _errmsg(sys.exc_info(), fnname, fstringstar=fstringstar)
        raise FStringenError(msg) from None

    output = locals_["_fstringstar"]
    return output


_original_excepthook = sys.excepthook


def exception_handler(exception_type, exception, traceback):
    # Traceback is useless, given the distortions we introduce
    if isinstance(exception, FStringenError):
        sys.stderr.write(f"{exception_type.__name__}: " +
                         f"{str(exception).strip()}\n")
    # For non fstringen-related errors however, traceback may be useful
    else:
        _original_excepthook(exception_type, exception, traceback)


sys.excepthook = exception_handler


def gen(model=None, fname=None, comment=None, notice=True):
    def realgen(fn):
        original_name = fn.__name__
        code = textwrap.dedent(inspect.getsource(fn))
        newcode = "\n".join(code.split("\n")[1:])  # Remove decorator
        original_code = newcode
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
            try:
                r = newgen(*args, **kwargs)
            # If the error is already an FStringenError, we have nothing to add
            except FStringenError as e:
                raise e from None
            except Exception:
                msg = _errmsg(sys.exc_info(), original_name,
                              code=original_code)
                raise FStringenError(msg) from None

            if r is None:
                return
            elif isinstance(r, str):
                v = textwrap.dedent(r)
                if len(v) > 0 and v[0] == "\n":
                    v = v[1:]
                if len(v) > 0 and v[-1] == "\n":
                    v = v[:-1]
                return v
            else:
                return r

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

        newfn.code = original_code
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


class Selectable:
    def __new__(cls, name, value, refindicator="#", root=None):
        # Pick Selectable methods that should be used
        methods = {}
        for method in cls.__dict__:
            if not method.startswith("__"):
                methods[method] = cls.__dict__[method]

        original_type = type(value)
        # Python does not allow subclassing bool, so we use an adapted int
        if type(value) == bool:
            value = int(value)

            def custom_repr_str(this):
                return str(bool(this.value))

            methods["__repr__"] = custom_repr_str
            methods["__str__"] = custom_repr_str

        # None cannot be subclassed either, use an empty string instead
        elif value is None:
            value = ""

            def custom_repr_str(this):
                return "None"

            def custom_eq(this, other):
                return other is None

            methods["__repr__"] = custom_repr_str
            methods["__str__"] = custom_repr_str
            methods["__eq__"] = custom_eq

        # New type will be a subclass of the value type, with the extra methods
        # defined in Selectable
        newcls = type(cls.__name__, (type(value),), methods)
        obj = newcls(value)
        # Initialize non-value attributes
        obj._initSelectable(name, original_type, refindicator, root)
        return obj

    def _initSelectable(self, name, original_type, refindicator, root):
        """ Sets internal Selectable values """
        self.name = name
        self.value = self
        self.type = original_type
        self.refindicator = refindicator
        self.root = root
        if self.root is None:
            self.root = self.value

    def _new(self, name, selectable):
        """ Instantiates a Selectable keeping the same root. """
        return Selectable(name, selectable, self.refindicator, self.root)

    @staticmethod
    def fromYAML(fname, refindicator="#", root=None):
        """ Loads a Selectable from a YAML file. """
        if yaml is None:
            raise FStringenError("Cannot find 'yaml' module")
        return Selectable(fname,
                          yaml.load(open(fname, "r").read(),
                                    Loader=yaml.Loader),
                          refindicator, root)

    @staticmethod
    def fromJSON(fname, refindicator="#", root=None):
        """ Loads a Selectable from a JSON file. """
        return Selectable(fname, json.loads(open(fname, "r").read()),
                          refindicator, root)

    @staticmethod
    def fromDict(dict_, name="dict", refindicator="#", root=None):
        """ Loads a Selectable from a Python dictionary. """
        return Selectable(name, dict_, refindicator, root)

    def has(self, path=None):
        """ Returns True if path exists in the Selectable. If path is None,
        returns True. """
        if path is None:
            return True  # We know we exist because we exist :-)
        callerctx = inspect.currentframe().f_back
        try:
            self.select(path, callerctx)
        except FStringenNotFound:
            return False

        return True

    def is_reference(self, path=None):
        """ Returns True if path is a possible reference. If path is None,
        returns True if this Selectable contains a reference. """
        if path is None:
            value = self.value
        else:
            callerctx = inspect.currentframe().f_back
            value = self.select(path, callerctx)
        return isinstance(value, str) and value.startswith(self.refindicator)

    def is_enabled(self, path=None):
        """ Returns True if path exists and its value is True. If path is None,
        returns True if this Selectable is True. """
        if path is None:
            value = self.value
        else:
            try:
                callerctx = inspect.currentframe().f_back
                value = self.select(path, callerctx)
            except FStringenError:
                return False

        return isinstance(value, int) and value != 0

    def select(self, path, callerctx=None):
        """ Returns a new Selectable based on path """

        if callerctx is None:
            callerctx = inspect.currentframe().f_back

        obj = self.value
        root = False
        # Ignore ref indicators and browse accordingly
        if path.startswith(self.refindicator):
            path = path[1:]
        # When an absolute path is used in a query, revert to the root
        if path.startswith("/"):
            path = path[1:]
            obj = self.root
            root = True
        # Empty path trailings are ignored
        if path.endswith("/"):
            path = path[:-1]

        parts = path.split("/")
        curpath = []
        if root:
            curpath.append("")

        lastpart = None

        for i in range(len(parts)):
            part = parts[i]

            # Replace <variables> with their values
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
                    raise FStringenError("Cannot iterate over '{}'".format(
                        "/".join(curpath[:-1])))
                elements = tuple(self._new(k, v) for k, v in obj.items())
                return self._new("*", elements)
            elif part.endswith("->"):
                part = part[:-2]
                newpath = obj[part]
                newselectable = self._new(part, obj)
                return newselectable.select(newpath, callerctx)
            else:
                if isinstance(obj, list) or isinstance(obj, tuple):
                    try:
                        part = int(part)
                    except ValueError:
                        raise FStringenError(
                            "Array navigation requires integers")
                elif not isinstance(obj, dict):
                    raise FStringenError(
                            "Cannot lookup path '{}' in value '{}'".format(
                                part, str(obj)))
                try:
                    obj = obj[part]
                except (KeyError, IndexError):
                    raise FStringenNotFound(
                        "Could not find path '{}' in '{}'".format(
                            "/".join(curpath), obj))

            lastpart = part

        return self._new(lastpart, obj)


Model = Selectable
