import sys; 
sys.path.append('../predict')
sys.path.append('../generator')
sys.path.append('../python')
from core import version, OsExpert, AppConfig
from app import App
from applogging import Log
from generator_app import GeneratorApp
from predictor import Predictor
from executor import Executor
import os
from pathlib import Path

@version(1,0,0)
class ExecuteApp(App):
	def __init__(self, version):
		super().__init__(__file__)
	def run(self, h5_filepath):
		self.executor = Executor(
			h5_filepath = h5_filepath,
			initial_capital = 1000, 
			initial_coins = 10
			).run_async().join()
if __name__ == '__main__':
	try:
		app = ExecuteApp()
		assert len(sys.argv) == 2, 'not exactly two parameters (i.e. one argument)'
		h5_filename = sys.argv[1]
		h5_filepath = os.path.join(AppConfig.setting('PREDICTOR_DATA_DIRPATH'), h5_filename)
		assert Path(h5_filepath).is_file(), 'is not a file: {}'.format(h5_filepath)
		app.run(h5_filepath)
	except KeyboardInterrupt:
		print('\n\nKeyboardInterrupt\n')
	except Exception as e:
		Log.c('app failed: {}', e)
		stacktrace = OsExpert.stacktrace()
		Log.d('stacktrace:\n{}', stacktrace)
