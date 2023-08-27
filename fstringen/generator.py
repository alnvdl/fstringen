import atexit
import inspect
import re
import sys
import textwrap
import traceback


class FStringenError(Exception):
    """
    FStringenError represents an error in generating text using gen.
    """
    pass


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
        newobj = []
        for el in obj:
            if el is None:
                continue
            el = textwrap.dedent(str(el)).replace("\n", "\n" + indent)
            newobj.append(el)
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
    if fstringstar is None and code is None and line:
        subfn = traceback.extract_tb(tb)[-1][2]
        return f"""
Error in function '{subfn}' called (directly or indirectly) by
generator '{fnname}':
{"-"*80}
Line {lineno + 1}: {line} <- {excl.__name__}: {str(exc).strip()}
{"-"*80}
"""
    if code is not None:
        fnlines = code.split("\n")
        startline = max(lineno - 3, 0)
        endline = min(lineno + 3, len(fnlines) - 1)
        try:
            fnlines[lineno] = (fnlines[lineno] +
                               f" <- {type(exc).__name__}: " +
                               f"{str(exc)}")
            msg = "\n".join(fnlines[startline:endline])
            if endline < len(fnlines) - 1:
                msg += "\n[...]"
        except IndexError:
            msg = ("[Could not determine source code location]\n" +
                   f"{type(exc).__name__}: {str(exc)}")

        return f"""
Error in generator '{fnname}':
{"-"*80}
{textwrap.dedent(msg).strip()}
{"-"*80}
"""

    if fstringstar is not None:
        return f"""
Error generating fstringstar in generator '{fnname}':
{"-"*80}
fstringstar: f\"\"\"*
{textwrap.dedent(fstringstar).strip()}
*\"\"\" <- {excl.__name__}: {str(exc).strip()}
{"-"*80}
"""


def _normalize_whitespace(fstringstar):
    if fstringstar[0] == "\n":
        fstringstar = textwrap.dedent(fstringstar)
        fstringstar = fstringstar[1:]

    lines = fstringstar.split("\n")
    if len(lines) >= 2 and lines[-1].strip() == "":
        lines = lines[:-1]
        fstringstar = "\n".join(lines)

    return fstringstar


def _compile(fstringstar):
    gen_frame = inspect.currentframe().f_back
    globals_ = gen_frame.f_globals
    locals_ = gen_frame.f_locals

    fstringstar = _normalize_whitespace(fstringstar)
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


def _exception_handler(exception_type, exception, traceback):
    # Traceback is useless, given the distortions we introduce
    if isinstance(exception, FStringenError):
        sys.stderr.write(f"{exception_type.__name__}: " +
                         f"{str(exception).strip()}\n")
    # For non fstringen-related errors however, traceback may be useful
    else:
        _original_excepthook(exception_type, exception, traceback)


sys.excepthook = _exception_handler


def gen(model=None, fname=None, preamble=None):
    """
    gen is a decorator that turns a function or method into a fstringen-powered
    generator.

    If model and fname are passed, the generator will pass model as the first
    and only argument to the decorated function, and write the value returned
    by that function to the file at fname. If preamble is not None, it will be
    included at the beginning of the generated file.
    """
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
                return textwrap.dedent(r)
            else:
                return r

        if model and fname:
            global _output
            _output[fname] = {
                "fn": newfn,
                "model": model,
                "preamble": preamble,
            }

        # Put the new function in globals, so other @gen code can call it.
        # This is obviously dangerous, and it's one of the the reasons why
        # fstringen must not be used in anything else other than generators.
        globals_[original_name] = newfn

        newfn.code = original_code
        return newfn

    return realgen


_output = {}  # type: ignore


def _generate_all():
    for fname in _output:
        genopts = _output[fname]
        f = open(fname, "w")
        if genopts["preamble"]:
            f.write(genopts["preamble"])
        fn = genopts["fn"]
        model = genopts["model"]
        f.write(fn(model))
        f.close()


atexit.register(_generate_all)


__all__ = "gen", "FStringenError"
