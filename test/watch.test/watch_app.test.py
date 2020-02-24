import sys; 
sys.path.append('../../src/fetch')
sys.path.append('../../src/python')
from app import App
import unittest
from core import OsExpert
from db import DatabaseGateway

class TestCase(unittest.TestCase):
	def setUp(self):
		self.db = DatabaseGateway()
		pass
	def test_watch_triggers_alert(self):
		raise NotImplementedError()
if __name__ == '__main__':
	parent_dirpath = OsExpert.path_backstep(__file__, backsteps=2) 
	App.initialize_in_dir(parent_dirpath)
	unittest.main()
    
