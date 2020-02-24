from applogging import Log
from core import AppConfig, OsExpert, NetworkExpert
from pathlib import Path
import os
import logging
	
class App():
	def __init__(self, appFilepath, isToNotifyStartup = True):
		print('App start: {}'.format(appFilepath))
		file_dirpath = OsExpert.path_backstep(appFilepath)
		parent_dirpath = OsExpert.path_backstep(file_dirpath)
		App.initialize_in_dirs(logconfig_dirpath=file_dirpath, appconfig_dirpath=parent_dirpath)
		if isToNotifyStartup is True:
			NetworkExpert.tryAppNotifyByEmail(appFilepath, 'service is starting')	
	@staticmethod
	def initialize_in_dir(dirpath):
		App.initialize_in_dirs(dirpath, dirpath)
	@staticmethod
	def initialize_in_dirs(appconfig_dirpath, logconfig_dirpath):
		OsExpert.ensure_abs_dirpath_exists(appconfig_dirpath)
		OsExpert.ensure_abs_dirpath_exists(logconfig_dirpath)
		App.initialize(
			appconfig_filepath = os.path.join(appconfig_dirpath, 'config.ini'), 
			logconfig_filepath = os.path.join(logconfig_dirpath, 'logconfig.json')
			)
	@staticmethod
	def initialize(appconfig_filepath, logconfig_filepath):
		OsExpert.ensure_abs_filepath_exists(appconfig_filepath)
		Log.initialize(logconfig_filepath)
		AppConfig.initialize(appconfig_filepath)     
