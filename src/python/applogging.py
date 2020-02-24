import inspect
import sys
import logging
from logging import config
import os
import json
from pathlib import Path

class Log:
	__logSubscriber = None
	__is_tracing_enabled = False
	__Logger = None
	__config_filename = 'logconfig.json'
	__default_configuration = {  
		    'version': 1,
		    'formatters': {
		        'custom': { 
		        	'format': '%(asctime)s %(levelname)s %(message)s',
		        	'datefmt': '%Y-%m-%d %H:%M:%S' 
		        	}
		        },
		    'handlers': {
		        'stdout':{
		            'class':'logging.StreamHandler',
		            'stream': 'python:sys.stdout', 	# Replace strm with stream if you're using python 2.7.
		            'formatter': 'custom'
		        }
		    },
		    'loggers': {
		        'default': {
		            'handlers': ['stdout'],
		            'level': 'python:logging.DEBUG',
		            'propagate': 'true',
		        	}
		    	}		
			}
	@staticmethod
	def initialize(logconfig_filepath, logSubscriber = None):
		Log.__Logger = Log.__get_logger(logconfig_filepath)
		Log.__logSubscriber = logSubscriber
	@staticmethod
	def _log(level, msg, args = None):
		if Log.__Logger is None:
			raise Exception('Logger has not been initialized')
		try:
			frm = inspect.stack()[2]
			if args is not None:
				if not isinstance(args, tuple):
					print('WARNING: Arguments is not of type "tuple" (type "{}" encountered)'.format(type(args)))
				else:
					if len(args) > 0:
						msg = msg.format(*args)
			formattedMsg = '{}:{} [{}] {}'.format(
					frm.filename, 
					frm.lineno, 
					frm[3],
					msg
					)
			Log.__Logger.log(level, formattedMsg)
			if Log.__logSubscriber is not None:
				try:
					Log.__logSubscriber(level, formattedMsg)
				except Exception as e:
					pass # silently ignore subscriber failure
		except Exception as e:
			print('A log statement failed: {}'.format(e))
	@staticmethod
	def __get_logger(logconfig_filepath):
		try:
			log_config = Log.__log_configuration(logconfig_filepath)
			Log.__dict_value_replace(log_config)
			config.dictConfig(log_config)
			logging.captureWarnings(True)
			logger = logging.getLogger('default') # TODO: does not fail if logger not present, but should
			return logger
		except Exception as e:
			raise Exception('Failed to get logger') from e
	@staticmethod
	def __log_configuration(logconfig_filepath):
		if not os.path.isabs(logconfig_filepath):
			raise ValueError('Path "{}" is not absolute'.format(logconfig_filepath))
		if not Path(logconfig_filepath).exists():
			raise ValueError('Path "{}" does not exist'.format(logconfig_filepath)) 
		if not Path(logconfig_filepath).is_file():
			raise ValueError('Path "{}" is not a file'.format(logconfig_filepath)) 
		print('Loading log configuration from file: {}'.format(logconfig_filepath))
		try:
			with open(logconfig_filepath, 'r') as f:
			    config_dict = json.load(f)
			    return config_dict
		except Exception as e:
			raise Exception('Failed to load log configuration from file') from e
	@staticmethod
	def __dict_value_replace(d):
		eval_prefix = 'python:'
		eval_prefix_length = len(eval_prefix)
		for key, value in d.items():
			if isinstance(value, dict):
				Log.__dict_value_replace(value)
			else:
				if isinstance(value, str) and value.startswith(eval_prefix):
					try:
						to_evaluate = value[eval_prefix_length:]
						if (to_evaluate.startswith('~/')):
							value = os.path.join(
								os.path.expanduser('~'), 
								to_evaluate[2:]
								)
						else:
							value = eval(to_evaluate)
						d[key] = value
					except Exception as e:
						raise Exception('Failed to evaluate dynamic log configuration value "{}" for key "{}"'.format(value, key))
	@staticmethod
	def tracing_enabled(value):
		Log.__is_tracing_enabled = value
	def t(msg, *args):
		if Log.__is_tracing_enabled == True:
			Log._log(logging.DEBUG, '(TRACE) {}'.format(msg), args) # TODO: implement trace, is currently just passing to debug
	def d(msg, *args):
		Log._log(logging.DEBUG, msg, args)
	@staticmethod
	def w(msg, *args):
		Log._log(logging.WARN, msg, args)
	@staticmethod
	def i(msg, *args):
		Log._log(logging.INFO, msg, args)
	@staticmethod
	def e(msg, *args):
		Log._log(logging.ERROR, msg, args)
	@staticmethod
	def c(msg, *args):
		Log._log(logging.CRITICAL, msg, args)
