"""Progressive evaluation.

Define a computational graph, either on the fly or via a class,
which is lazily evaluated as objects are requested.

Examples:
    Consider the following computation:

    b = a**2 - 4
    c = b - a


"""
__version__ = '1.0.0'
from .progressive import ProgEval

__all__ = ['ProgEval']
