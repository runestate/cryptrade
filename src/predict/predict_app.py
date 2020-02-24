import sys; 
sys.path.append('../generator')
sys.path.append('../python')
from core import version, OsExpert, AppConfig, OsExpert, FileWatcher
from app import App
from applogging import Log
from generator_app import GeneratorApp
from predictor import Predictor
import os
from pathlib import Path
import pandas as pd
import time
import sys

@version(1,0,0)
class PredictApp(App):
	def __init__(self, version):
		super().__init__(__file__)
	def handle_change(self):
		Log.d('modified')
	def run(self, h5_filepath):
		predictor = Predictor(h5_filepath)
		thread = predictor.run_async()
		thread.join()
if __name__ == '__main__':
	try:
		app = PredictApp()
		assert len(sys.argv) == 2, 'not exactly two parameters (i.e. one argument)'
		h5_filename = sys.argv[1]
		h5_filepath = os.path.join(AppConfig.setting('GENERATOR_DATA_DIRPATH'), h5_filename)
		assert Path(h5_filepath).is_file(), 'is not a file: {}'.format(h5_filepath)
		app.run(h5_filepath)
	except KeyboardInterrupt:
		print('\n\nKeyboardInterrupt\n')
	except Exception as e:
		Log.c('app failed: {}', e)
		stacktrace = OsExpert.stacktrace()
		Log.d('stacktrace:\n{}', stacktrace)
