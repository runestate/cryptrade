import sys; 
sys.path.append('../../src/fetch')
sys.path.append('../../src/python')
from app import App
import unittest
from core import AppConfig, OsExpert, ObjectExpert, StringExpert
from db import DatabaseGateway
import os

class TestCase(unittest.TestCase):
	def setUp(self):
		self.db = DatabaseGateway()
		pass
	def test_dict_has_keys(self):
		ObjectExpert.ensure_dict_keys(
			{ 'a': 1, 'b': 2, 'c': 3 },
			[ 'a', 'b', 'c']
			)
	def test_dict_does_not_have_all_expected_keys(self):
		with self.assertRaises(ValueError):
			ObjectExpert.ensure_dict_keys(
				{ 'a': 1, 'b': 2, 'c': 3 },
				[ 'a', 'b', 'c', 'z']
				)
	def test_dict_has_unexpected_keys(self):
		with self.assertRaises(ValueError):
			ObjectExpert.ensure_dict_keys(
				{ 'a': 1, 'b': 2, 'c': 3 },
				[ 'a' ]
				)
	def test_file_contents_md5hash(self):
		tempFilepath = os.path.join(
			AppConfig.setting('TEMP_DIRPATH'), 
			'file.txt'
			)
		with open(tempFilepath,'w') as f:
			f.write('sample text')
		self.assertEqual(
			OsExpert.md5(tempFilepath),
			'70ee1738b6b21e2c8a43f3a5ab0eee71'
			)
		os.remove(tempFilepath)
	def test_string_md5hash(self):
		self.assertEqual(
			StringExpert.md5hash('sample text'),
			'70ee1738b6b21e2c8a43f3a5ab0eee71'
			)
if __name__ == '__main__':
	parent_dirpath = OsExpert.path_backstep(__file__, backsteps=2) 
	App.initialize_in_dir(parent_dirpath)
	unittest.main()
    
