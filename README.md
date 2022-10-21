[![Tests](https://github.com/mathisgerdes/progeval/actions/workflows/python-test.yml/badge.svg)](https://github.com/mathisgerdes/progeval/actions/workflows/python-test.yml)
[![Documentation Status](https://readthedocs.org/projects/progeval/badge/?version=latest)](https://progeval.readthedocs.io/en/latest/?badge=latest)

# Progressive evaluation

[**Documentation**](https://progeval.readthedocs.io/)
| [**Installation**](#installation)
| [**Examples**](#examples)
| [**Related**](#related)

This package lets the user define a computation such that:
1. Depending on the requested output, only the required (partial) computations are executed.
2. Intermediate quantities can be overriden by the user such that dependent values are recomputed.

The computational graph can either be defined as a class, or is constructed dynamically by registering nodes.

## Installation

To use progeval, it can be installed with pip:

```bash
(.venv) $ pip install progeval
```

## Examples
Consider the following toy computation:
```
alpha = x * y
beta = x + y
total = alpha + beta
```

We can define this computational graph in multiple ways, all via the computational graph class `ProgEval`.
The first is by dynamically adding nodes corresponding to the computable objects:

```python
from progeval import ProgEval

graph = ProgEval()
graph.alpha = lambda x, y: x * y
graph.beta = lambda x, y: x + y
graph.total = lambda alpha, beta: alpha + beta

# we can then set inputs ...
graph.x, graph.y = 3, 6
# ... and evaluate any (intermediate) value
graph.total == 27
```

The above example relies on the fact that the inputs (`x`, `alpha`, etc.) can be read from the function signatures.
If we want to reuse some external function this is not possible.
The following syntax allows one to (optionally) specify the input arguments:

```python
from progeval import ProgEval


def add(x, y):
    return x + y


graph = ProgEval()
graph.register('alpha', lambda x, y: x * y)
graph.register('beta', add)
# here the inputs we want are different from the names 
# in the function definition of `add`
graph.register('total', add, ['alpha', 'beta'])
```

Another way to define the computational graph is by collecting all parts of the computation as methods of a class:

```python
from progeval import ProgEval


class Computation(ProgEval):

    def __init__(self, x, y):
        super().__init__(x=x, y=y)

    @staticmethod
    def alpha(x, y):
        return x * y

    @staticmethod
    def beta(x, y):
        return x + y

    @staticmethod
    def total(alpha, beta):
        return alpha + beta

# The class then acts almost like a normal function
Computation(3, 8).total == 35
```

## Related
A similar functionality of delayed evaluation of a computational graph is provided by [Dask delayed](https://docs.dask.org/en/stable/delayed.html).
However, the construction is slightly different.
There, the graph is built dynamically by replacing intermediate quantities with `Delayed` objects and wrapping functions.
The functionality of `Dask`, which is intended for computational parallelism, can even be combined with the structures here, as shown in the how-to section of the documentation.
