import sys
sys.path.append('../python')
sys.path.append('..')
import os
import asyncio
from app import App
from applogging import Log
from core import AppConfig, OsExpert, StringExpert
from data import Store, DuplicateInsertException
from db import DuplicateInsertException
import traceback
import time
import os
from os.path import basename
import subscribe
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from threading import Thread
from pathlib import Path
import pandas as pd

class ParseUtil:
	def __init__(self, subscribers, db):
		self.subscribers = subscribers
		self.store = db
	def subscriber_by_filename(self, filename): 
		assert filename, 'input filename not specified'
		for parser in self.subscribers:
			if filename.startswith(parser.handler_filename):
				return parser
		raise ValueError('Could not determine subscriber for filename "{}"'.format(filename))
	def process_api_response_file(self, filepath, subscriber, datafetch_api_response=None): 
		db = self.store
		filename = os.path.basename(filepath)
		if not os.path.isfile(filepath) or not filename.startswith(subscriber.handler_filename):
			return False
		receiveTimestamp = int(ParseUtil.extractTimestampText(filename))
		with open(filepath, 'r') as disk_file:
			response_text = disk_file.read()
			response_text_md5hash = StringExpert.md5hash(response_text)					
			if datafetch_api_response is None:
				datafetch_api_response = ParseUtil.partial_datafetch_api_response(subscriber, db)
			datafetch_api_response = {
				**datafetch_api_response,
				'response': response_text,
				'response_md5hash': response_text_md5hash,
				'epoch_receive_time': receiveTimestamp,
				'response_filename': filename
			}
			transaction = None
			try:	
				datafetch_api_response_id = db.create_datafetch_api_response(datafetch_api_response)
			except DuplicateInsertException as e:
				Log.d('db rejected api_response_id as a duplicate: {}', response_text_md5hash)
				return False
			except Exception as e:
				Log.e('Failed to store api_response ({})', response_text_md5hash)
				raise e
			ParseUtil.parse_and_persist_as_transaction_maybe(datafetch_api_response, subscriber, db)
		return True
	@staticmethod
	def partial_datafetch_api_response(subscriber, db):
		handler_abs_filepath = os.path.realpath(subscriber.handler_filepath)
		exchange_name = subscriber.exchange_prefix + subscriber.market_name()
		return  {
			'datafetch_api_id': db.datafetch_api_id_by_handler_filepath(handler_abs_filepath, create_if_nonexisting = True),
			'datasource_id': db.datasource_id_by_name(subscriber.datasource_name),
			'exchange_id': db.exchange_id_by_name(exchange_name),
			'from_currency_id': db.currency_id_by_code(subscriber.from_currency_code),
			'to_currency_id': db.currency_id_by_code(subscriber.to_currency_code)
		}
	@staticmethod
	def parse_and_persist_as_transaction_maybe(datafetch_api_response, parser, db):
		try:
			transaction = ParseUtil.__parse_and_persist_as_transaction(datafetch_api_response, parser, db)
		except DuplicateInsertException as e:
			Log.w('db rejected transaction as a duplicate: {}', datafetch_api_response)
			return False
		except Exception as e:
			Log.e('Failed to parse and store transaction from api_response: {}', datafetch_api_response)
			raise e		
		return True
	def __parse_and_persist_as_transaction(row, parser, db):
		parsed = parser.parse(row)
		if parsed is None:
			return None
		parser_datasource_name = parser.datasource_name
		id = db.create_transaction(parsed)
		Log.t('persisted transaction id {}', id)
		return parsed
	@staticmethod
	def extractTimestampText(filename):
		tokens = filename.split('.')
		if (len(tokens) == 3 and tokens[1].isdigit() and tokens[2] == 'response'):
			return int(tokens[1])
		if (len(tokens) == 2 and tokens[1].isdigit()):
			return int(tokens[1])
		tokens = filename.split('_')
		if (len(tokens) > 1 and tokens[len(tokens) -1].isdigit()):
			return int(tokens[len(tokens) -1])
		raise ValueError('Could not extract timestamp for filename tokens {}'.format(tokens))
class DirWatcher(FileSystemEventHandler):
	__callbacks = []
	def __init__(self, callback): 
		super().__init__()
		DirWatcher.__callbacks.append(callback)
	@staticmethod
	def on_created(event):
		if event.is_directory:
			return None
		filepath = event.src_path
		for callback in DirWatcher.__callbacks:
			callback(filepath)
class ParseApp(App):
	def __init__(self):
		super().__init__(__file__)
		Log.d('construct')
		self.dir_path = AppConfig.setting('DATA_RESPONSE_DIRPATH')
		self.store = Store()
		self.subscribers = subscribe.all()
		self.parse_util = ParseUtil(self.subscribers, self.store)
	def get_or_create_hdf5(self):
		filepath = AppConfig.setting('DATASTORE_HDF5_FILEPATH')
		file = Path(filepath)
		exists = file.exists()
		if exists:
			assert file.is_file(), 'hdf5 filepath exists but is not a file'
		pd.set_option('io.hdf.default_format','table')
		hdf5 = pd.HDFStore(filepath, append=True)
		hdf5.swmr_mode = True # may or may not have an effect
		return hdf5
	def handle_file_created(self, filepath):
		filename = os.path.basename(filepath)
		subscriber = self.parse_util.subscriber_by_filename(filename)
		is_parsed = self.parse_util.process_api_response_file(filepath, subscriber)
		Log.i('file {} was parsed: {}', filepath, is_parsed)
	def detect_and_parse_new_disk_files_async(self):
		Log.i('asynchronously detecting and parsing new disk files')
		event_handler = DirWatcher(self.handle_file_created)
		self.observer = Observer()
		self.observer.schedule(event_handler, self.dir_path, recursive=False)
		self.observer.start()
		return self.observer
	def parse_existing_disk_files(self):
		Log.d('initiating parsing of disk files')
		storeCount = 0
		fileCount = 0
		files = list(os.scandir(self.dir_path))
		total_file_count = len(files)
		Log.d('file count: {}', total_file_count)
		for subscriber in self.subscribers:
			Log.d('parsing disk files for provider: {}', subscriber.handler_filename)
			subscriber_store_count = 0
			subscriber_file_count = 0
			subscriber_partial_datafetch_api_response = self.parse_util.partial_datafetch_api_response(subscriber, self.store)
			for file in files:
				subscriber_file_count += 1
				if self.parse_util.process_api_response_file(file.path, subscriber, subscriber_partial_datafetch_api_response) is True:
					subscriber_store_count += 1
				if subscriber_file_count % 5000 == 0:
					percent_done = 100 * subscriber_file_count / total_file_count 
					Log.d('...processed {}/{} disk files for subscriber {} ({:.1f}% done)', subscriber_store_count, subscriber_file_count, subscriber.handler_filename, percent_done)
			Log.d('done parsing {}/{} disk files for subscriber {}', subscriber_store_count, subscriber_file_count, subscriber.handler_filename)
			storeCount += subscriber_store_count
			fileCount += subscriber_file_count
		Log.d('done, parsed {}/{} disk files for all subscribers', storeCount, fileCount)
	def process_nonparsed_api_responses_full(self, sleep_seconds=0):		
		Log.i('initiating continuous parsing of api responses with subset sleep interval: {} seconds', sleep_seconds)
		try:
			min_id = -1
			next_min_id = 0
			while next_min_id > min_id:
				min_id = next_min_id
				parse_count = 0
				next_min_id = self.process_nonparsed_api_responses_subset(next_min_id = min_id)
				time.sleep(sleep_seconds)
		except Exception as e:
			raise Exception('Failed to process nonparsed api responses') from e
		transaction_count = self.store.transaction_count()
		Log.d('no more api responses to parse, transaction count is now {}', transaction_count)
	def process_nonparsed_api_responses_subset(self, next_min_id = 0):
		limit = 1000
		Log.i('processing nonparsed api responses, starting from id {} with limit {}', next_min_id, limit)
		total_row_count = 0
		parse_count = 0
		is_to_keep_fetching = True
		while is_to_keep_fetching == True:			
			datasources_frame = self.store.datasources_frame() 
			frame = self.store.unparsed_datafetch_api_responses_frame(min_id=next_min_id, limit=1000)
			row_count = frame.shape[0]
			if row_count == 0:
				is_to_keep_fetching = False
			else:
				total_row_count += row_count
				for i, row in frame.iterrows():
					try:
						row_id = row['id']
						datasource_id = row['datasource_id']
						parser = self.find_parser(datasource_id, datasources_frame)
						if ParseUtil.parse_and_persist_as_transaction_maybe(row, parser, self.store) == True:
							parse_count += 1
					except Exception as e:
						raise Exception('Failed to parse row index {} with id {}'.format(i, row_id)) from e
				ids = frame['id']
				max_id = ids.max()
				Log.t('sweep of ids {}..{} returned {} entries', next_min_id, max_id, row_count)
				next_min_id = max_id + 1 # start from the next row
		Log.i('search for nonparsed responses done, parse count: {}/{}', parse_count, total_row_count)
		return next_min_id
	def find_parser(self, datasource_id, datasources_frame):
		for p in self.subscribers:
			datasource_name = p.datasource_name
			parser_datasource_id = self.store.datasource_id_by_name(datasource_name, datasources=datasources_frame)
			if parser_datasource_id == datasource_id:
				return p
		raise ValueError('No parser available for datasource id {}', datasource_id)
if __name__ == '__main__':
	app = ParseApp()
	try:
		app.parse_existing_disk_files()
	except KeyboardInterrupt:
		print('\n\nKeyboardInterrupt\n')
	except Exception as e:
		Log.c('app failed')
		stacktrace = traceback.format_exc()
		Log.d('exception stack:\n{}', stacktrace)
