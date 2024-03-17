class ModelError(Exception):
    """
    ModelError represents an error in navigating a model with Model.select.
    """

    pass


def _is_enumerable(obj):
    try:
        enumerate(obj)
    except TypeError:
        return False
    else:
        return True


def _has_items_method(obj):
    items = getattr(obj, "items", None)
    return items and callable(items)


# _none represents "None" internally, allowing Model.select to return a
# default of None just like dict.get.
_none = object()


class Model:
    """
    Model represents any named (name) Python object (value). It acts as a
    subclass of the type of the value object. If that object is a dict-like or
    is enumerable, a special path syntax can be used to navigate it using
    Model.select. If the value contains the special prefix denoted by
    refprefix, that value can be used to jump to other parts of the model by
    using Model.select. Calling the model directly is equivalent to calling
    Model.select.
    """

    def __new__(cls, name, value, refprefix="#", _root=None):
        # Pick Model methods that should be used.
        methods = {}
        for method in cls.__dict__:
            if not method.startswith("__") or method == "__call__":
                methods[method] = cls.__dict__[method]

        original_type = type(value)
        # Python does not allow subclassing bool, so we use an adapted int.
        if isinstance(value, bool):
            value = int(value)

            def custom_repr_str(this):
                return str(bool(this.value))

            methods["__repr__"] = custom_repr_str
            methods["__str__"] = custom_repr_str

        # None cannot be subclassed either, use an empty string instead.
        elif value is None:
            value = ""

            def custom_repr_str(this):
                return "None"

            def custom_eq(this, other):
                return other is None

            methods["__repr__"] = custom_repr_str
            methods["__str__"] = custom_repr_str
            methods["__eq__"] = custom_eq

        # Create a dynamic class based on the original type of the value, but
        # including methods from Model.
        # See: https://docs.python.org/3/library/functions.html#type
        newcls = type(cls.__name__, (type(value),), methods)
        obj = newcls(value)
        # Initialize Model attributes.
        obj._initModel(name, original_type, refprefix, _root)
        return obj

    def _initModel(self, name, original_type, refprefix, root):
        """
        Sets internal Model values
        """
        self.name = name
        self.value = self
        self.type = original_type
        self.refprefix = refprefix
        self.root = root
        if self.root is None:
            self.root = self.value

    def _new(self, name, model):
        """
        _new instantiates a Model keeping the same root.
        """
        return Model(name, model, self.refprefix, self.root)

    def has(self, path=None):
        """
        has returns True if path exists in the Model. If path is None, returns
        True.
        """
        if path is None:
            return True
        try:
            self._select(path)
        except ModelError:
            return False

        return True

    def is_reference(self, path=None):
        """
        is_reference returns True if path is a possible reference. If path is
        None, returns True if the value of this Model contains a reference.
        """
        if path is None:
            value = self.value
        else:
            value = self._select(path)
        return isinstance(value, str) and value.startswith(self.refprefix)

    def is_enabled(self, path=None):
        """
        if_enabled returns True if path exists and its value is True. If path
        is None, returns True if the value of this Model is True.
        """
        if path is None:
            value = self.value
        else:
            try:
                value = self._select(path)
            except ModelError:
                return False

        return isinstance(value, int) and value != 0

    def select(self, path, default=_none):
        """
        select returns a new Model based on path, with an optional default
        value in case the path is valid but cannot be not found.
        """
        return self._select(path, default)

    # Make model(...) a shortcut for model.select(...).
    __call__ = select

    def _select(self, path, default=_none):
        obj = self.value
        name = None
        curpath = []

        # Ignore ref indicators and navigate accordingly.
        if path.startswith(self.refprefix):
            path = path[1:]
            if path.endswith("->"):
                path = path[:-2]
                return self._select(path, default)
        # When an absolute path is used in a query, revert to the root.
        if path.startswith("/"):
            path = path[1:]
            obj = self.root
            curpath.append("")
        # Empty path trailings are ignored.
        if path.endswith("/"):
            path = path[:-1]

        parts = path.split("/")
        for i in range(len(parts)):
            part = parts[i]
            curpath.append(part)
            if part == "*" and i == len(parts) - 1:
                if _has_items_method(obj):
                    elements = tuple(self._new(k, v) for k, v in obj.items())
                elif _is_enumerable(obj):
                    elements = type(obj)(
                        self._new(str(i), v) for i, v in enumerate(obj)
                    )
                else:
                    raise ModelError(
                        "Cannot iterate over '{}'".format("/".join(curpath[:-1]))
                    )
                obj = elements
                name = "*"
            elif part.endswith("->"):
                part = part[:-2]
                newpath = obj[part]
                newmodel = self._new(part, obj)
                obj = newmodel._select(newpath, default)
                name = obj.name
            else:
                try:
                    obj = obj[part]
                except TypeError:
                    if not _is_enumerable(obj):
                        raise ModelError(
                            "Cannot lookup path '{}' in value '{}'".format(
                                part, str(obj)
                            )
                        )
                    try:
                        part = int(part)
                    except ValueError:
                        raise ModelError("Enumerable navigation requires integers")
                    try:
                        obj = obj[part]
                    except IndexError:
                        if default is not _none:
                            obj = default
                            break
                        raise ModelError(
                            "Could not find path '{}' in '{}'".format(
                                "/".join(curpath), obj
                            )
                        )
                except KeyError:
                    if default is not _none:
                        obj = default
                        break
                    raise ModelError(
                        "Could not find path '{}' in '{}'".format(
                            "/".join(curpath), obj
                        )
                    )
                name = part

        return self._new(name, obj)


__all__ = "Model", "ModelError"
