# except translate
STR_FUNCS = ["capitalize", "casefold", "center", "count", "encode", "endswith", "expandtabs", "find", "format", "format_map", "index", "isalnum", "isalpha", "isascii", "isdecimal", "isdigit", "islower", "isnumeric", "isprintable", "isspace", "istitle", "isupper", "join", "ljust", "lower", "lstrip", "maketrans", "partition", "replace", "rfind", "rindex", "rjust", "rpartition", "rsplit", "rstrip", "split", "splitlines", "startswith", "strip", "swapcase", "title", "upper", "zfill"]


def _wrap_str_funcs(base, funcname):
    def wrapper(*args, **kwargs):
        return getattr(base.name(), funcname)(*args, **kwargs)

    return wrapper


class Base(object):
    def __init__(self, *args, **kwargs):
        super(Base, self).__init__()
        for sf in STR_FUNCS:
            if not hasattr(self, sf):
                setattr(self, sf, _wrap_str_funcs(self, sf))

    def name(self):
        raise NotImplementedError("'name' is not implemented yet")

    def __eq__(self, other):
        return self.__hash__() == other.__hash__()

    def __repr__(self):
        return "{}<'{}'>".format(self.__class__.__name__, self.name())

    def __str__(self):
        return self.name()

    def __add__(self, value):
        return self.name().__add__(value)

    def __radd__(self, value):
        return value + self.name()

    def __contains__(self, key):
        return self.name().__contains__(key)

    def __format__(self, format_spec):
        return self.name().__format__(format_spec)

    def __ge__(self, value):
        return self.name().__ge__(value)

    def __gt__(self, value):
        return self.name().__gt__(value)

    def __le__(self, value):
        return self.name().__le__(value)

    def __len__(self):
        return self.name().__len__()

    def __lt__(self, value):
        return self.name().__lt__(value)

    def __mod__(self, value):
        return self.name().__mod__(value)

    def __mul__(self, value):
        return self.name().__mul__(value)

    def __ne__(self, value):
        return self.name().__ne__(value)

    def __rmod__(self, value):
        return self.name().__rmod__(value)

    def __rmul__(self, value):
        return self.name().__rmul__(value)

    def __sizeof__(self):
        return self.name().__sizeof__()


class Node(Base):
    pass


class Attr(Base):
    pass


class Geom(Base):
    def toStringList(self):
        raise NotImplementedError("{}.toStringList is not implemented yet".format(self.__class.__name__))
