import unittest
from .mti import make_attempt, Prober


class TestAttempt(unittest.TestCase):

    def test_no_result(self):
        q = {
            'result': None,
            'answers': [1, 2, 3],
            'multi': False,
            'iter': 3
        }
        self.assertEqual(
            make_attempt(q), {1: '0', 2: '1', 3: '1'},
            msg="Error when no result")

    def test_has_result(self):
        q = {
            'result': {1: '1', 2: '0', 3: '0'},
            'answers': [1, 2, 3],
            'multi': False,
            'iter': 3
        }
        self.assertEqual(
            make_attempt(q), {1: '1', 2: '0', 3: '0'},
            msg="Error when have result")


class TestProber(unittest.TestCase):

    def test_shuffle_with_err_single(self):
        a = Prober({
            'a': {
                'result': None,
                'answers': [1, 2, 3],
                'multi': False,
                'iter': 2
            }
        })
        a.shuffle_results(['a'])
        self.assertEqual(a.questions, {
            'a': {
                'result': None,
                'answers': [1, 2, 3],
                'multi': False,
                'iter': 4  # 2 << 1
            }
        }, msg="Error inc when not multi")

    def test_shuffle_with_err_multi(self):
        a = Prober({
            'a': {
                'result': None,
                'answers': [1, 2, 3],
                'multi': True,
                'iter': 2
            }
        })
        a.shuffle_results(['a'])
        self.assertEqual(a.questions, {
            'a': {
                'result': None,
                'answers': [1, 2, 3],
                'multi': True,
                'iter': 3  # 2 + 1
            }
        }, msg="Error inc when not multi")

    def test_shuffle_with_err_result(self):
        a = Prober({
            'a': {
                'result': {1: '1', 2: '0', 3: '0'},
                'answers': [1, 2, 3],
                'multi': False,
                'iter': 2
            }
        })
        a.shuffle_results(['b'])
        self.assertEqual(
            a.questions,
            {
                'a': {
                    'result': {1: '1', 2: '0', 3: '0'},
                    'answers': [1, 2, 3],
                    'multi': False,
                    'iter': 2
                }
            }, msg="Error: inc when have result")
