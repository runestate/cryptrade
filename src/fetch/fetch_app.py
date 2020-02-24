import sys
sys.path.append('../python')
sys.path.append('..')
import os
import asyncio
from app import App
from applogging import Log
from core import AppConfig, OsExpert, StringExpert, NetworkExpert
import traceback
from subscriber_result import SubscriberResult
import time
import subscribe

class FetchApp(App):
	RESPONSE_EXTENSION='response'
	def __init__(self):
		super().__init__(__file__)
		Log.d('construct')
		retry_delay_seconds = int(AppConfig.setting('DATAFETCH_API_RETRY_DELAY_SECONDS'))
		data_response_dirpath = AppConfig.setting('DATA_RESPONSE_DIRPATH')
		Log.d('data response dirpath is: {}', data_response_dirpath)
		self.retry_delay_seconds = retry_delay_seconds
		self.data_response_dirpath = data_response_dirpath
		OsExpert.ensure_abs_dirpath_exists(data_response_dirpath)
		self.subscribers = subscribe.all()
	def activateSubscribers(self):
		subscriber_count = len(self.subscribers)
		Log.i('activating {} subscriber(s)', subscriber_count)
		loop = asyncio.get_event_loop()
		futures = [self.__process_subscriber(i, s) for i,s in enumerate(self.subscribers)]
		tasks = asyncio.gather(*futures)
		loop.run_until_complete(tasks)
		loop.close()
		Log.i('done processing subscribers')
	async def __process_subscriber(self, index, subscriber):
		fail_count = 0
		response_file_prefix = subscriber.handler_filename
		while True:
			try:
				Log.i('invoking subscriber {}', subscriber.handler_filename)				
				async for response_text in subscriber.subscribe():
					response_text_md5hash = StringExpert.md5hash(response_text)					
					try:
						epoch = int(time.time())
						filepath = os.path.join(
							self.data_response_dirpath,
							'{}.{}.{}'.format(response_file_prefix, epoch, FetchApp.RESPONSE_EXTENSION)
							)
						with open(filepath, 'w') as file:
							file.write(response_text)
					except Exception as e:
						Log.e('Failed to save response to file, message: {}', e)
					Log.d('stored api response for subcriber {} (hash {})', subscriber.handler_filename, response_text_md5hash)
			except Exception as e:
				fail_count += 1
				Log.e('failed to invoke subscriber {} ({} failures so far)', subscriber.handler_filename, fail_count)
				stacktrace = traceback.format_exc()
				Log.d('exception stack:\n{}', stacktrace)
				Log.i('retrying in {} seconds..', self.retry_delay_seconds)
				await asyncio.sleep(self.retry_delay_seconds)
if __name__ == '__main__':
	try:
		app = FetchApp()
		app.activateSubscribers()
	except KeyboardInterrupt:
		print('\n\nKeyboardInterrupt\n')
	except Exception as e:
		Log.c('app failed')
		stacktrace = traceback.format_exc()
		Log.d('exception stack:\n{}', stacktrace)
		
