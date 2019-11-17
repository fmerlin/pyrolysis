import unittest
from datetime import date, datetime
from pyrolysis.common.converter import Converter
from dataclasses import dataclass, field


@dataclass
class TestObject:
    name: str = field()
    id: int = field()


class TestService(unittest.TestCase):
    def setUp(self):
        self.converter = Converter()
        self.converter.register(TestObject)

    def test_str_convert(self):
        self.assertEqual(self.converter.str_convert(1), '1')
        self.assertEqual(self.converter.str_convert('a'), 'a')
        self.assertEqual(self.converter.str_convert(date(2017, 1, 1)), '2017-01-01')
        self.assertEqual(self.converter.str_convert(datetime(2017, 1, 1)), '2017-01-01T00:00:00')
        self.assertEqual(self.converter.str_convert(True), 'True')
        self.assertEqual(self.converter.str_convert([1, 'A', True]), '1,A,True')

    def test_str_revert(self):
        self.assertEqual(self.converter.str_revert('1', 'int', False), 1)
        self.assertEqual(self.converter.str_revert('a', 'str', False), 'a')
        self.assertEqual(self.converter.str_revert('2017-01-01', 'date', False), date(2017, 1, 1))
        self.assertEqual(self.converter.str_revert('2017-01-01T00:00:00', 'datetime', False), datetime(2017, 1, 1))
        self.assertEqual(self.converter.str_revert('True', 'bool', False), True)
        self.assertEqual(self.converter.str_revert('1,2,3', 'int', True), [1, 2, 3])

    def test_json_convert(self):
        self.assertEqual(self.converter.json_convert(1), '1')
        self.assertEqual(self.converter.json_convert('a'), '"a"')
        self.assertEqual(self.converter.json_convert(True), 'true')
        self.assertEqual(self.converter.json_convert({'a': 1}), '{"a": 1}')
        self.assertIn(self.converter.json_convert(TestObject(name='hello', id=1), sort_keys=True),
                         ['{"id": 1, "name": "hello"}','{"name": "hello", "id": 1}'])

    def test_json_revert(self):
        self.assertEqual(self.converter.json_revert('1', 'int'), 1)
        self.assertEqual(self.converter.json_revert('"a"', 'str'), 'a')
        self.assertEqual(self.converter.json_revert('true', 'bool'), True)
        self.assertEqual(self.converter.json_revert('[1,2,3]', 'int'), [1, 2, 3])
        self.assertDictEqual(self.converter.json_revert('{"a": 1}', 'dict'), {'a': 1})
        self.assertEqual(self.converter.json_revert('{"name": "hello", "id": 1}', 'TestObject'),
                         TestObject(name='hello', id=1))

    def test_xml_convert(self):
        self.assertEqual(self.converter.xml_convert(1), '<int>1</int>')
        self.assertEqual(self.converter.xml_convert('a'), '<str>a</str>')
        self.assertEqual(self.converter.xml_convert(True), '<bool>True</bool>')
        self.assertEqual(self.converter.xml_convert({'a': 1}), '<dict><a type="int">1</a></dict>')
        self.assertIn(self.converter.xml_convert(TestObject(name='hello', id=1)),
                         ['<TestObject><id type="int">1</id><name>hello</name></TestObject>',
                          '<TestObject><name>hello</name><id type="int">1</id></TestObject>'])

    def test_xml_revert(self):
        self.assertEqual(self.converter.xml_revert('<int>1</int>', 'int'), 1)
        self.assertEqual(self.converter.xml_revert('<str>a</str>', 'str'), 'a')
        self.assertEqual(self.converter.xml_revert('<bool>True</bool>', 'bool'), True)
        self.assertDictEqual(self.converter.xml_revert('<dict><a type="int">1</a></dict>', 'dict'), {'a': 1})
        self.assertEqual(
            self.converter.xml_revert('<TestObject><name>hello</name><id type="int">1</id></TestObject>', 'TestObject'),
            TestObject(name='hello', id=1))

    def test_csv_convert(self):
        self.assertEqual(self.converter.csv_convert([{'a': 1, 'b': 2}, {'a': 3, 'b': 4}]), 'a,b\n1,2\n3,4\n')
        self.assertEqual(self.converter.csv_convert([TestObject(name='a', id=1), TestObject(name='b', id=2)]),
                         'id,name\n1,a\n2,b\n')

    def test_csv_revert(self):
        self.assertEqual(self.converter.csv_revert('a,b\n1,2\n3,4', 'dict'),
                         [{'a': '1', 'b': '2'}, {'a': '3', 'b': '4'}])
        self.assertEqual(self.converter.csv_revert('name,id\na,1\nb,2', 'TestObject'),
                         [TestObject(name='a', id=1), TestObject(name='b', id=2)])


if __name__ == '__main__':
    unittest.main()
