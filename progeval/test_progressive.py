import unittest
from progeval import ProgEval
from collections import defaultdict


class TestProgEval(unittest.TestCase):
    def test_class(self):
        call_count = defaultdict(int)

        class Computation(ProgEval):
            # mix pure and non-pure functions
            def beta(self):
                call_count['beta'] += 1
                return self.alpha + 3

            @staticmethod
            def gamma(alpha, beta):
                call_count['gamma'] += 1
                return alpha + beta

        # check values and number of function calls
        graph = Computation()
        graph.alpha = 5
        self.assertEqual(graph.alpha, 5)
        self.assertEqual(call_count['beta'], 0)
        self.assertEqual(call_count['gamma'], 0)
        self.assertEqual(graph.gamma, 2 * 5 + 3)
        self.assertEqual(call_count['beta'], 1)
        self.assertEqual(call_count['gamma'], 1)
        self.assertEqual(graph.beta, 5 + 3)
        self.assertEqual(call_count['beta'], 1)
        self.assertEqual(call_count['gamma'], 1)

        # different call order
        call_count.clear()
        graph = Computation()
        graph.alpha = 5
        self.assertEqual(graph.beta, 5 + 3)
        self.assertEqual(call_count['beta'], 1)
        self.assertEqual(call_count['gamma'], 0)
        self.assertEqual(graph.gamma, 2 * 5 + 3)
        self.assertEqual(call_count['beta'], 1)
        self.assertEqual(call_count['gamma'], 1)

    def test_class_init(self):
        call_count = defaultdict(int)

        class Computation(ProgEval):
            def __init__(self, alpha):
                super().__init__()
                self.alpha = alpha

            # mix pure and non-pure functions
            def beta(self):
                call_count['beta'] += 1
                return self.alpha + 3

            @staticmethod
            def gamma(alpha, beta):
                call_count['gamma'] += 1
                return alpha + beta

        # check values and number of function calls
        graph = Computation(5)
        self.assertEqual(graph.alpha, 5)
        self.assertEqual(call_count['beta'], 0)
        self.assertEqual(call_count['gamma'], 0)
        self.assertEqual(graph.gamma, 2 * 5 + 3)
        self.assertEqual(call_count['beta'], 1)
        self.assertEqual(call_count['gamma'], 1)
        self.assertEqual(graph.beta, 5 + 3)
        self.assertEqual(call_count['beta'], 1)
        self.assertEqual(call_count['gamma'], 1)

    def test_class_transformer(self):
        registered = set()

        def register(function, static, name):
            registered.add((name, static))
            return function

        class Computation(ProgEval, transformer=register):
            def __init__(self, alpha):
                super().__init__()
                self.alpha = alpha

            # mix pure and non-pure functions
            def beta(self):
                return self.alpha + 3

            @staticmethod
            def gamma(alpha, beta):
                return alpha + beta

        graph = Computation(5)
        self.assertEqual(graph.gamma, 2 * 5 + 3)
        self.assertEqual(registered, {
            ('alpha', True),  # alpha is static (returns set value)
            ('beta', False),  # beta is not defined as alpha static function
            ('gamma', True)})

    def test_class_recompute(self):

        class Computation(ProgEval):
            def beta(self):
                return self.alpha + 3

            @staticmethod
            def gamma(alpha, beta):
                return alpha + beta

        graph = Computation()
        graph.alpha = 5
        self.assertEqual(graph.gamma, 2 * 5 + 3)
        graph.beta = 10  # override value
        self.assertEqual(graph.gamma, 5 + 10)
        del graph.beta  # remove again, forcing re-computation of beta
        self.assertEqual(graph.gamma, 2 * 5 + 3)

    def test_dynamic(self):
        call_count = defaultdict(int)

        def compute_beta(alpha):
            call_count['beta'] += 1
            return alpha + 3

        def compute_gamma(alpha, beta):
            call_count['gamma'] += 1
            return alpha + beta

        graph = ProgEval()
        graph.register('alpha', 5)
        graph.register('beta', compute_beta)
        graph.register('gamma', compute_gamma)

        # check values and number of function calls
        self.assertEqual(graph.alpha, 5)
        self.assertEqual(call_count['beta'], 0)
        self.assertEqual(call_count['gamma'], 0)
        self.assertEqual(graph.gamma, 2 * 5 + 3)
        self.assertEqual(call_count['beta'], 1)
        self.assertEqual(call_count['gamma'], 1)
        self.assertEqual(graph.beta, 5 + 3)
        self.assertEqual(call_count['beta'], 1)
        self.assertEqual(call_count['gamma'], 1)

        # alternative way of assigning initial values
        call_count.clear()
        graph = ProgEval()
        graph.register('beta', compute_beta)
        graph.register('gamma', compute_gamma)
        graph.alpha = 5

        self.assertEqual(graph.alpha, 5)
        self.assertEqual(call_count['beta'], 0)
        self.assertEqual(call_count['gamma'], 0)
        self.assertEqual(graph.gamma, 2 * 5 + 3)
        self.assertEqual(call_count['beta'], 1)
        self.assertEqual(call_count['gamma'], 1)
        self.assertEqual(graph.beta, 5 + 3)
        self.assertEqual(call_count['beta'], 1)
        self.assertEqual(call_count['gamma'], 1)

    def test_dynamic_assign(self):
        call_count = defaultdict(int)

        def compute_beta(alpha):
            call_count['beta'] += 1
            return alpha + 3

        def compute_gamma(alpha, beta):
            call_count['gamma'] += 1
            return alpha + beta

        graph = ProgEval()
        graph.alpha = 5
        graph.beta = compute_beta
        graph.gamma = compute_gamma

        # check values and number of function calls
        self.assertEqual(graph.alpha, 5)
        self.assertEqual(call_count['beta'], 0)
        self.assertEqual(call_count['gamma'], 0)
        self.assertEqual(graph.gamma, 2 * 5 + 3)
        self.assertEqual(call_count['beta'], 1)
        self.assertEqual(call_count['gamma'], 1)
        self.assertEqual(graph.beta, 5 + 3)
        self.assertEqual(call_count['beta'], 1)
        self.assertEqual(call_count['gamma'], 1)

    def test_dynamic_transformer(self):
        registered = set()

        def register(function, static, name):
            registered.add((name, static))
            return function

        call_count = defaultdict(int)

        def compute_beta(alpha):
            call_count['beta'] += 1
            return alpha + 3

        def compute_gamma(alpha, beta):
            call_count['gamma'] += 1
            return alpha + beta

        graph = ProgEval(transformer=register)
        graph.alpha = 5
        graph.register('beta', compute_beta)
        graph.register('gamma', compute_gamma)

        # all functions are static for dynamically created computational graphs
        self.assertEqual(
            registered, {('alpha', True), ('beta', True), ('gamma', True)})

    def test_dynamic_reassign(self):
        graph = ProgEval()
        graph.alpha = lambda x: 2 * x + 1
        graph.beta = lambda y: y * y
        graph.gamma = lambda alpha, beta, y: alpha * beta - y

        # first run
        graph.x, graph.y = 3, 8
        self.assertEqual(graph.gamma, 440)

        # second run
        graph.x, graph.y = 3, 4
        self.assertEqual(graph.gamma, 108)


if __name__ == '__main__':
    unittest.main()
