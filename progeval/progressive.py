from __future__ import annotations

from inspect import signature, Signature
from typing import Callable, Union, Optional, Any, Sequence
from collections import defaultdict


def _make_property(name, fun, static, transformer, args=None) -> property:
    """Create a property object from a generator function."""
    sig_args = list(signature(fun).parameters)
    if transformer is not None:
        fun = transformer(fun, static, name)
        if isinstance(fun, tuple):
            fun, sig = fun
            sig_args = list(sig.parameters)
    # explicitly passed args have precedence
    args = sig_args if args is None else args
    if not static:
        args = args[1:]

    def delete(self):
        try:
            del self._store[name]
        except KeyError:
            pass
        if self._track_dependence and name in self._dependencies:
            for dep in self._dependencies[name]:
                delattr(self, dep)
            self._dependencies[name].clear()

    def setter(self, val):
        delete(self)  # delete it's value and dependent's values
        self._store[name] = val

    def getter(self):
        try:
            return self._store[name]
        except KeyError:
            arg_vals = [getattr(self, arg) for arg in args]

            # add current quantity to all requested arguments
            # NOTE: If function is not static, can't track dependence via self!
            if self._track_dependence:
                for arg in args:
                    self._dependencies[arg].append(name)

            val = fun(*arg_vals) if static else fun(self, *arg_vals)
            setter(self, val)
            return val

    return property(getter, setter, delete, fun.__doc__)


class ProgEvalMeta(type):
    """Metaclass for progressive evaluation.

    Replaces all functions of a class with properties that internally
    manage the cache of already-computed values in the instance's
    _store dictionary. Attributes that are not callable are ignored,
    as are any attributes starting with an underscore.
    """
    def __new__(mcs, cls_name, bases, attrs,
                track_dependence=True, transformer=None):
        # Skip for ProgressiveEvaluation base class
        if len(bases) == 0:
            return super().__new__(mcs, cls_name, bases, attrs)

        for attr in attrs:
            fun = attrs[attr]
            static = False
            if isinstance(fun, staticmethod):
                fun = fun.__func__
                static = True
            if attr.startswith('_') or not callable(fun):
                continue

            attrs[attr] = _make_property(attr, fun, static, transformer)

        attrs['_track_dependence'] = track_dependence
        attrs['_transformer'] = staticmethod(transformer)
        return super().__new__(mcs, cls_name, bases, attrs)


def _identity(name, val):
    def identity():
        return val
    identity.__name__ = name
    return identity


class ProgEval(metaclass=ProgEvalMeta):
    _track_dependence: bool = None
    # mustn't change signature
    _transformer: Callable[[Callable, bool, str],
                           Union[Callable, tuple[Callable, Signature]]] = None

    def __init__(
            self,
            track_dependence: Optional[bool] = None,
            transformer: Callable[
                [Callable, bool, str],
                Union[Callable, tuple[Callable, Signature]]] = None,
            **initial_values):
        self.__dict__['_store'] = {}
        self.__dict__['_dynamic_nodes'] = {}
        self.__dict__['_dependencies'] = defaultdict(list)
        if track_dependence is not None:
            self.__dict__['_track_dependence'] = track_dependence
        if transformer is not None:
            self.__dict__['_transformer'] = transformer
        for key, value in initial_values.items():
            setattr(self, key, value)

    def register(self, name, function: Union[Callable, Any],
                 args: Sequence[str] = None):
        if not callable(function):
            self._store[name] = function
            function = _identity(name, function)
        prop = _make_property(name, function, True, self._transformer, args)
        self._dynamic_nodes[name] = prop

    def compute_all_quantities(self):
        outputs = {}
        for name, obj in type(self).__dict__.items():
            if isinstance(obj, property):
                outputs[name] = getattr(self, name)

        for name, prop in self._dynamic_nodes.items():
            outputs[name] = prop.fget(self)

        return outputs

    def __getattr__(self, key):
        try:
            val = self._dynamic_nodes[key]
        except KeyError:
            raise AttributeError(f'{key} is not a registered quantity')
        return val.fget(self)

    def __setattr__(self, key, value):
        if key in self.__dict__:
            raise RuntimeError(f'overriding attribute {key} is not supported')

        if callable(value):
            try:
                del self._store[key]
            except KeyError:
                pass  # doesn't matter if it existed or not
            self.register(key, value)
            return

        try:  # try to set value of class-level property
            obj = type(self).__dict__[key]
            if not isinstance(obj, property):
                raise RuntimeError(
                    f'overriding attribute {key} is not supported')
            print('setting parent property value')
            obj.fset(self, value)
        except KeyError:
            try:  # try to set value of dynamically added property
                self._dynamic_nodes[key].fset(self, value)
            except KeyError:
                # create a new node in the computational graph
                self._store[key] = value
                self.register(key, _identity(key, value))

    def __delattr__(self, key):
        try:  # try to delete value of (class-level) property
            obj = type(self).__dict__[key]
            if isinstance(obj, property):
                obj.fdel(self)
            return
        except KeyError:
            pass

        try:  # try to delete value of dynamically added property
            self._dynamic_nodes[key].fdel(self)
        except KeyError:
            pass

        try:  # try to delete instance object
            del self.__dict__[key]
            return
        except KeyError:
            raise AttributeError(f'{key} is not a registered quantity')
