import sys; 
sys.path.append('../fetch')
sys.path.append('../python')
from db import DatabaseGateway
from core import OsExpert, Timespan, AppConfig
from app import App
from applogging import Log
import time

class WatchApp():
	def __init__(self):
		Log.d('construct')
		self.db = DatabaseGateway()
	def watch_continuously(self, watch_interval_seconds):	
		Log.i('continuous watching activated with interval of {} seconds', watch_interval_seconds)
		consecutive_error_count = 0
		while True:
			try:
				self.__verify_datafetch_apis_write_frequency()
				consecutive_error_count = 0
			except Exception as e:
				consecutive_error_count += 1
				Log.e('fail during watcher check ({} consecutive errors)', consecutive_error_count)
				stacktrace = OsExpert.stacktrace()
				Log.d('stacktrace:\n{}', stacktrace)
			time.sleep(watch_interval_seconds)
	def __verify_datafetch_apis_write_frequency(self):
		Log.d('watcher check initiating')
		datafetch_apis_frame = self.db.datafetch_api_view_frame()
		if datafetch_apis_frame.empty:
			Log.d('no datafetch apis to watch')
		else:
			exceed_count = 0
			for i, row in datafetch_apis_frame.iterrows():
				datafetch_api_id = row['id']
				write_idle_seconds = row['write_idle_seconds']
				result_frequency_seconds = row['result_frequency_seconds']
				if write_idle_seconds > result_frequency_seconds:
					exceed_count += 1
					idle_time_str = Timespan.from_seconds(write_idle_seconds).as_string()
					warn_message = 'datafetch api id {} has exceeded its {} second limit (idle time {})'.format(datafetch_api_id, result_frequency_seconds, idle_time_str)
					Log.w(warn_message)
			Log.d('watch check done, exceed count: {}', exceed_count)
if __name__ == '__main__':
	file_dirpath = OsExpert.path_backstep(__file__)
	parent_dirpath = OsExpert.path_backstep(file_dirpath)
	App.initialize_in_dirs(logconfig_dirpath=file_dirpath, appconfig_dirpath=parent_dirpath)
	try:
		WatchApp().watch_continuously(watch_interval_seconds = 15)
	except KeyboardInterrupt:
		print('\n\nKeyboardInterrupt\n')
	except Exception as e:
		Log.c('app failed: {}', e)
		stacktrace = OsExpert.stacktrace()
		Log.d('stacktrace:\n{}', stacktrace)
