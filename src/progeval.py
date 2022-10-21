from __future__ import annotations

from inspect import signature, Signature
from typing import Callable, Union, Optional, Any, Sequence
from collections import defaultdict

__version__ = '1.0.0'


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

    return property(getter, setter, delete, getattr(fun, '__doc__', None))


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
    _track_dependence: bool = True
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
        """This class implements a cached computational graph.

        Nodes of the computational graph are only evaluated if they
        are requested and values are cached to avoid re-computation.
        If the graph is changed (by re-assigning nodes), only parts
        that depend on the change are re-evaluated.

        Computational graphs can be created in two ways:

        - Dynamically, by assigning nodes to a ``ProgEval()`` object.
          Assignments can be made either as e.g. ``graph.x = lambda a: 2*a``,
          or by invoking ``graph.register(name, function)``.
        - Statically, by subclassing ProgEval. All class methods that do not
          start with an underscore are interpreted as computational nodes.

        The two methods can also be mixed.

        Args:
            track_dependence: Whether to track dependence in the graph.
                The default is true. If set to false, changing the
                computational graph will not force dependent values to
                be re-computed.
            transformer: Can be used to transform every computational node
                in the graph. The function must take the function, whether
                it is static, and the name as inputs. Static indicates
                whether the first argument of the function is `self`,
                i.e. an instance of the computational graph.
                The output must be a function with the same call signature,
                or a tuple of the modified function and the new call signature.
            **initial_values: Input values can be set in a convenient way
                by passing them as arguments here. This is equivalent to
                setting them afterwards via e.g. ``self.x = x``.
        """
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
                 args: Sequence[str] = None) -> None:
        """Add a new node to the computational graph.

        The given function specifies how to compute the quantity with
        the given name. If the second argument is not callable, it is
        instead interpreted as the value of the quantity.

        If the third argument is given, it specifies the quantities
        that must be computed first and passed to the function.
        Otherwise, this is automatically derived from the argument names
        of the function.

        Args:
            name: Name of node/quantity in computational graph.
            function: Specifies how to compute the quantity or is its value.
            args: Overrides the argument names of the function.
        """
        if self._track_dependence:
            try:
                delattr(self, name)  # this will recursively reset dependents
            except AttributeError:
                pass  # wasn't a registered quantity

        if not callable(function):
            self._store[name] = function
            function = _identity(name, function)
        prop = _make_property(name, function, True, self._transformer, args)
        self._dynamic_nodes[name] = prop

    def compute_all_quantities(self) -> dict[str, Any]:
        """Evaluate all quantities in the computational graph.

        Returns:
            A dictionary mapping the name of the quantity to its value.
        """
        outputs = {}
        for name, obj in type(self).__dict__.items():
            if isinstance(obj, property):
                outputs[name] = getattr(self, name)

        for name, prop in self._dynamic_nodes.items():
            outputs[name] = prop.fget(self)

        return outputs

    def clear_cache(self):
        """Remove all cached values of the computational graph."""
        for prop in self._dynamic_nodes.values():
            prop.fdel(self)

        for prop in type(self).__dict__.values():
            if isinstance(prop, property):
                prop.fdel(self)

    def __getattr__(self, key):
        """Get attribute of computational graph.

        This is only invoked if looking up class attributes and
        elements in self.__dict__ failed. Thus, only need to check
        whether ``key`` is a dynamically registered node.
        """
        if key in type(self).__dict__:
            # This can only happen if the evaluation of the function
            # set by the user raises an AttributeError. Python then
            # tries to call __getattr__, assuming that `key` doesn't exist.
            # But really, the AttributeError should be raised. Otherwise,
            # the true underlying error is obscured by and it would appear
            # the node isn't registered.
            return type(self).__dict__[key].fget(self)

        try:
            val = self._dynamic_nodes[key]
        except KeyError:
            raise AttributeError(f'{key} is not a registered quantity')
        return val.fget(self)

    def __setattr__(self, key, value):
        """Set attribute of computational graph.

        Arguments in self.__dict__ must not be overridden as they ensure
        the computational graph behaves as expected. All supported assignments
        must either set the value of an existing node or create a new node.
        """
        if key in self.__dict__:
            raise RuntimeError(f'overriding attribute {key} is not supported')

        is_quantity = not callable(value)

        try:  # try to set value of class-level property
            obj = type(self).__dict__[key]
        except KeyError:
            pass  # handled below
        else:
            if not isinstance(obj, property):
                raise RuntimeError(
                    f'overriding attribute {key} is not supported')
            if is_quantity:
                obj.fset(self, value)
                return

        if is_quantity:
            try:  # try to set value of dynamically added property
                self._dynamic_nodes[key].fset(self, value)
                return
            except KeyError:
                self._store[key] = value
                # need to create a new (dummy) node
                value = _identity(key, value)

        # set dynamic node (precedence over statically defined properties)
        self.register(key, value)

    def __delattr__(self, key):
        """Delete cached value of nodes in computational graph.

        The computational structure of the graph is kept, only the values
        that were computed previously are deleted.
        """
        try:  # try to delete value of (class-level) property
            obj = type(self).__dict__[key]
            if isinstance(obj, property):
                obj.fdel(self)
            return
        except KeyError:
            pass

        try:  # try to delete value of dynamically added property
            self._dynamic_nodes[key].fdel(self)
            return
        except KeyError:
            raise AttributeError(f'{key} is not a registered quantity')

        # Do not support deleting values from self.__dict__ as assignment
        # is also not supported.


__all__ = ['ProgEval']
