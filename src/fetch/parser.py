import sys; sys.path.append('..')
import os
import asyncio
from applogging import Log
from core import AppConfig, OsExpert
import traceback
import time

AppConfig.initialize_in_file_dir(
	OsExpert.path_backstep(__file__)
	)     

class Parser():
	def __init__(self):
		wfPath = "/tmp/my_fifo2"
		while True:
			with open(wfPath, 'r') as fp:
				line = fp.readline()
				while line:
					print('read: ' + line)
					line = fp.readline()
			print('not open')
if __name__ == '__main__':
	try:
		Parser()
	except KeyboardInterrupt:
		print('\n\nKeyboardInterrupt\n')
