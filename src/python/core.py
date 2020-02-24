from configparser import ConfigParser, ExtendedInterpolation
from pathlib import Path
import os
from applogging import Log
import json
import hashlib
import signal
import traceback 
from ssl import SSLContext, PROTOCOL_TLSv1_2
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys
import smtplib
from email.message import EmailMessage
from enum import Enum     # for enum34, or the stdlib version
import socket
from datetime import datetime
import time
from multiprocessing import Event
import pandas as pd
from threading import Thread
from functools import wraps

class ClassVersion:
	def __init__(self, major, minor, bugfix, build):
		self.major = major
		self.minor = minor
		self.bugfix = bugfix
		self.build = build
def version(*expected_args):
	def decorator(func):
		@wraps(func)
		def wrapper(*args, **kwargs):
			if len(expected_args) != 3:
				raise ValueError('Version decorator did not receive exactly three arguments')
			major = expected_args[0]
			minor = expected_args[1]
			bugfix = expected_args[2]
			build = int(time.time())
			assert isinstance(major, int), 'major version was not a number'
			assert isinstance(minor, int), 'minor version was not a number'
			assert isinstance(bugfix, int), 'bugfix version was not a number'
			assert isinstance(build, int), 'build version was not a number'
			return func(*args, **kwargs, version=ClassVersion(major, minor, bugfix, build))
		return wrapper
	return decorator
class Market(Enum):
	Local = 1
	Global = 2
def prettyJson(jsonData):
	return json.dumps(jsonData, indent=4, sort_keys=True)
class NetworkExpert:
	@staticmethod
	def tryAppNotifyByEmail(serviceName, messsage):
		if AppConfig.setting('IS_EMAIL_NOTIFICATION_ENABLED') != '1':
			Log.d('ignoring email request per configuration')
			return False
		alertEmail = AppConfig.setting('ALERT_EMAIL')
		hostName = socket.gethostname()
		return NetworkExpert.emailMaybe(alertEmail, alertEmail, '*** {}: {} ***'.format(hostName, serviceName), messsage)
	@staticmethod
	def emailMaybe(sender, receiver, title, text, smtp_host=None, smtp_user=None, smtp_password=None, smtp_port=587):
		try:			
			NetworkExpert.email(sender, receiver, title, text, smtp_host, smtp_user, smtp_password, smtp_port)
			return True
		except Error:
			Log.e('Failed to send email')
			return False
	def email(sender, receiver, title, text, smtp_host=None, smtp_user=None, smtp_password=None, smtp_port=587):
		try:
			if smtp_host is None:
				smtp_host = AppConfig.setting('SMTP_HOST')
			if smtp_user is None:
				smtp_user = AppConfig.setting('SMTP_USER')
			if smtp_password is None:
				smtp_password = AppConfig.setting('SMTP_PASSWORD')
			msg = EmailMessage()
			msg.set_content(text)
			msg['Subject'] = title
			msg['From'] = sender #Address(display_name='Recipient', addr_spec='rcpt@example.org')
			msg['To'] = receiver
			Log.t('sending email')
			with smtplib.SMTP(host=smtp_host, port=smtp_port) as smtp_server:
				smtp_server.starttls(context=SSLContext(PROTOCOL_TLSv1_2))
				smtp_server.login(user=smtp_user, password=smtp_password)
				smtp_server.send_message(msg)
				smtp_server.quit()
			Log.t('sent email')
		except Exception as e:				
			raise Exception('Failed to send email') from e
class Timespan:
	def __init__(self, hour=0, minute=0, second=0):
		self.hour = hour
		self.minute = minute
		self.second = second
	def as_string(self):
		return '{:d}:{:02d}:{:02d}'.format(self.hour, self.minute, self.second)
	@staticmethod
	def from_seconds(seconds):
		m, s = divmod(seconds, 60)
		h, m = divmod(m, 60)
		return Timespan(hour=h, minute=m, second=s)
class Timeout:
	def __init__(self, seconds=1, error_message='Timeout'):
		self.seconds = seconds
		self.error_message = error_message
	def handle_timeout(self, signum, frame):
		raise TimeoutError(self.error_message)
	def __enter__(self):
		signal.signal(signal.SIGALRM, self.handle_timeout)
		signal.alarm(self.seconds)
	def __exit__(self, type, value, traceback):
		signal.alarm(0)
from html.parser import HTMLParser

class MLStripper(HTMLParser):
	def __init__(self):
		super().__init__()
		self.reset()
		self.strict = False
		self.convert_charrefs= True
		self.fed = []
	def handle_data(self, d):
		self.fed.append(d)
	def get_data(self):
		return ''.join(self.fed)
class StringExpert:
	@staticmethod
	def strip_tags(html):
		s = MLStripper()
		s.feed(html)
		return s.get_data()
	@staticmethod
	def prettify_json(json_data):
		return json.dumps(json_data, indent=4, sort_keys=True)
	@staticmethod
	def md5hash(string):
		hash_md5 = hashlib.md5()
		hash_md5.update(string.encode())
		return hash_md5.hexdigest()
	@staticmethod
	def format_timestamp(timestamp):
		return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
class ObjectExpert:
	@staticmethod
	def ensure_dict_keys(d, expected_keys):
		if d is None:
			raise ValueError('Object was not defined')
		if not isinstance(d, dict):
			raise TypeError('Input object not of type dictionary')
		if expected_keys is None:
			raise ValueError('Expected dictionary keys not defined')
		input_keys = d.keys()
		missing_input_keys = []
		for expected_key in expected_keys:
			if not expected_key in input_keys:
				missing_input_keys.append(expected_key)
		if len(missing_input_keys) > 0:
			raise ValueError('One or more required keys were missing ({})'.format(
				','.join(missing_input_keys)
				))
		unexpected_input_keys = []
		for input_key in input_keys:
			if not input_key in expected_keys:
				unexpected_input_keys.append(input_key)
		if len(unexpected_input_keys) > 0:
			raise ValueError('Encountered one or more unexpected input keys ({})'.format(
				','.join(unexpected_input_keys)
				))
class H5FileWatcher:
	def __init__(self, h5_filepath, row_handler, contraints_dict=None): 
		self.handle_event = Event()
		self.h5_filepath = h5_filepath
		self.handle_count = 0
		self.job_frames = {}
		self.last_handle_count = None
		self.row_handler = row_handler
		self.contraints_clause = '' if contraints_dict is None else ' '.join('and {}={}'.format(k,v) for k,v in contraints_dict.items())
		Log.d('cc: {}', self.contraints_clause)
		assert row_handler
	def handle_change(self):
		self.handle_count += 1
		Log.d('file change event {}', self.handle_count)
		self.handle_event.set()
	def ensure_strictly_increasing_index(self, df):
		p = None
		for i,r in df.iterrows():
			assert p is None or p < i, '{} < {}'.format(p, i)
			p = i		
	def process_h5(self):
		with pd.HDFStore(self.h5_filepath, mode='r') as h5:		
			for jobuid in h5:
				is_first_encounter = jobuid not in self.job_frames
				if is_first_encounter == True:
					self.job_frames[jobuid] = pd.read_hdf(h5, jobuid, start=0, stop=1) # fetch first row to get the first index/epoch
				job_df = self.job_frames[jobuid]
				latest_epoch = job_df.index.values[-1] # will ensure we don't 'miss' any rows in case the handle count jumps more than once	
				where_clause = 'index > {} {}'.format(latest_epoch, self.contraints_clause) 
				new_df = pd.read_hdf(h5, jobuid, where=where_clause)
				if new_df.empty:
					Log.w('dataset was empty for key {} and index > {}', jobuid, latest_epoch)
				else:
					assert new_df.index.values[0] > latest_epoch
					new_first_index = 0 if is_first_encounter == True else len(job_df)
					joined = pd.concat([job_df, new_df])
					self.job_frames[jobuid] = joined
					if len(joined) > 100000:
						Log.w('holding a dataset of significant length ({} rows, {:.1f}mb): {}', len(joined), joined.memory_usage().sum()/1_000_000, jobuid)
					assert joined.shape[0] == len(job_df) + len(new_df)
					self.ensure_strictly_increasing_index(joined) # TODO: remove once this is confirmed
					self.row_handler(jobuid, joined, new_first_index)
	def trigger(self):
		self.handle_event.set()
	def __run(self):
		Log.d('Watching file: {}', self.h5_filepath)
		thread = FileWatcher(self.h5_filepath, modified=self.handle_change).run_async()
		try:
			while self.handle_event.wait():
				if self.last_handle_count is not None:
					jump_count = self.handle_count - self.last_handle_count
					if jump_count > 1:
						Log.w('handle count has jumped {} times than once since the last processing', jump_count)
				self.last_handle_count = self.handle_count
				self.process_h5()
				self.handle_event.clear()
		finally:
			Log.w('run loop broken, unwatching file: {}', self.h5_filepath)
			thread.stop()
			thread.join()
	def run_async(self):
		thread = Thread(target=self.__run)
		thread.start()
		return thread
class FileWatcher(FileSystemEventHandler):
	def __init__(self, filepath, modified=None): 
		super().__init__()
		self.filepath = filepath
		self.modified = modified
	def on_modified(self, event):
		if self.modified is not None and event.src_path == self.filepath:
			self.modified()
	def run_async(self):
		path = Path(self.filepath)
		dirpath = str(path.parent)
		assert path.is_file
		observer = Observer()
		observer.schedule(self, dirpath, recursive=False)
		observer.start()
		return observer
	
class OsExpert:
	@staticmethod
	def prompt_confirm(question):
		while True:
			print(question +' (y/n): ')
			reply = str(input()).lower().strip()
			if reply[:1] == 'y':
				return True
			if reply[:1] == 'n':
				return False
			print("\nThe answer is invalid")
	@staticmethod
	def sibling_filepath(filepath, sibling_filename, backstep = 0):
		sibling_dirpath = OsExpert.path_backstep(filepath, backsteps = backstep +1)
		return os.path.join(sibling_dirpath, sibling_filename)
	@staticmethod
	def path_backstep(filepath, backsteps = 1):
		dirPath = filepath
		while backsteps > 0:
			dirPath = os.path.abspath(
				os.path.join(dirPath, os.pardir)
				)
			backsteps -= 1
		return dirPath
	@staticmethod
	def md5(filepath):
		hash_md5 = hashlib.md5()
		with open(filepath, "rb") as f:
			for chunk in iter(lambda: f.read(4096), b""):
				hash_md5.update(chunk)
		return hash_md5.hexdigest()
	@staticmethod
	def ensure_abs_path_exists(path):
		if not os.path.isabs(path):
			raise ValueError('Path "{}" is not absolute'.format(path))
		if not Path(path).exists():
			raise ValueError('Path "{}" does not exist'.format(path)) 
	@staticmethod
	def ensure_abs_filepath_exists(path):
		OsExpert.ensure_abs_path_exists(path)
		if not Path(path).is_file():
			raise ValueError('Path "{}" is not a file'.format(path)) 
	@staticmethod
	def ensure_abs_dirpath_exists(path):
		OsExpert.ensure_abs_path_exists(path)
		if not Path(path).is_dir():
			raise ValueError('Path "{}" is not a directory'.format(path)) 
	@staticmethod
	def stacktrace():
		return traceback.format_exc()
class AppConfig:
	Filepath = None
	@staticmethod
	def initialize(filepath):
		AppConfig.__ensure_config_filepath_valid(filepath)
		AppConfig.Filepath = filepath
		startup_message = 'Configuration filepath: {}'.format(AppConfig.Filepath)
		Log.i(startup_message)
	@staticmethod
	def __ensure_config_filepath_valid(filepath):
		if filepath == '':
			raise ValueError('Input filepath was the empty string')
		if filepath is None:
			raise ValueError('Configuration filepath not initialized')
		if not os.path.isabs(filepath):
			raise ValueError('Configuration filepath "{}" is not absolute'.format(filepath))
		if not Path(filepath).is_file():
			raise ValueError('Configuration filepath "{}" does not exist'.format(filepath)) 
	@staticmethod
	def setting(key):
		filepath = AppConfig.Filepath
		if filepath is None:
			raise ValueError('The configuration filepath has not been set')
		AppConfig.__ensure_config_filepath_valid(filepath)
		config = ConfigParser(interpolation = ExtendedInterpolation())
		config.read(filepath)
		for section in config.sections():
			config.set(section, 'HOME', os.path.expanduser('~'))
		configSettings = config['SETTINGS']
		return configSettings[key]
			
