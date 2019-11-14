import unittest

from pyrolysis.common import doc


class TestDoc(unittest.TestCase):
    def test_doc(self):
        f = """
        method

        desc long
        desc long2

        :param p: test1
        :raise Excp: test2
        :return: test
        """

        summary, desc, doc_params, doc_return, doc_excep = doc.parse_docstring(f)

        self.assertEqual(summary, "method")
        self.assertEqual(desc, "desc long\n" "desc long2")
        self.assertEqual(doc_params, {'p': 'test1'})
        self.assertEqual(doc_return,"test")
        self.assertEqual(doc_excep, {'Excp': 'test2'})


if __name__ == '__main__':
    unittest.main()
