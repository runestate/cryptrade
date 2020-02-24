import sys; sys.path.append('..')
import os
import asyncio
from applogging import Log
from core import AppConfig, OsExpert, Timeout
import traceback
import time

AppConfig.initialize_in_file_dir(
	OsExpert.path_backstep(__file__)
	)     

class Parser():
	def __init__(self):
		wfPath = "/tmp/my_fifo2"
		wp = None
		try:
			if not os.path.exists(wfPath):	
				os.mkfifo(wfPath)
			while True:
				is_sent = False
				try:
					with Timeout(1):
						with open(wfPath, 'w') as wp:
							print('sending..')
							wp.write("a write!\n")		
						print('sent')
						is_sent = True
						time.sleep(1)
				except TimeoutError:
					if not is_sent:
						print('timeout')
		except OSError as e:
			raise Exception('OSError') from e
if __name__ == '__main__':
	try:
		Parser()
	except KeyboardInterrupt:
		print('\n\nKeyboardInterrupt\n')
