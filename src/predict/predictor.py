import sys; 
sys.path.append('../generator')
sys.path.append('../python')
sys.path.append('..')
from db import DatabaseGateway, Datasource, Exchange, Currency
from core import OsExpert, Timespan, AppConfig, StringExpert, FileWatcher, H5FileWatcher, version
from app import App
from applogging import Log
import time
from collections import deque, namedtuple
import pandas as pd
from datetime import datetime
from os import path 
from pathlib import Path
import os
import sys
from generator_app import GeneratorApp
from numpy import nan, isnan
import time
from multiprocessing import Event
import os 
from pathlib import Path    
from numpy import nan, float64
import warnings
from tables import NaturalNameWarning
from sklearn.metrics import accuracy_score
import time
from ensemble_predictor import EnsemblePredictor

@version(1,0,0)
class Predictor:
	def __init__(self, h5_filepath, version):
		warnings.simplefilter('ignore', NaturalNameWarning)
		h5_inputfile = Path(h5_filepath)
		output_dirpath = AppConfig.setting('PREDICTOR_DATA_DIRPATH')
		self.h5_out_filepath = os.path.join(output_dirpath, h5_inputfile.name)
		h5_out_file =  Path(self.h5_out_filepath)
		if h5_out_file.exists():
			Log.i('overwrite file?: {}', h5_out_file)
			if not OsExpert.prompt_confirm('File already exists, overwrite? {}'.format(h5_out_file)):
				Log.d('user aborted, exiting')
				exit()
			Log.w('removing file: {}', h5_out_file)
			os.remove(self.h5_out_filepath)
		self.predictors_map = {}
		base_filepath = output_dirpath
		with pd.HDFStore(h5_filepath, mode='r') as h5: 	
			keys = h5.keys()
			Log.i('h5 input keys: {}', keys)
			assert len(keys) == 1, 'harcoded restriction on single key was violated'
			for key in keys:
				Log.i('row count for {}: {}', key, h5.get_storer(key).nrows)
				self.predictors_map[key] = [
				EnsemblePredictor(min_predict_generator_size=2000, max_train_size=5000)
				]		
		self.h5_watcher = H5FileWatcher(h5_filepath, self.handle_job_epoch, {'is_simulated': 0})
	def filter_simulated_observations(self, df):
		filtered_df = df[df['is_simulated'] != 1]
		dropped = df[~df.index.isin(filtered_df.index)]
		if len(dropped) > 0:
			Log.w('filtered out {} simulated frames', len(dropped))
		else:
			Log.d('no simulated frames found to filter out')
		return filtered_df
	def handle_job_epoch(self, jobuid, df, start_index):
		Log.d('handling block starting at index {} for key: {}', start_index, jobuid)
		try:
			df = self.filter_simulated_observations(df)
			if len(df) == 0:	
				Log.w('no rows to process')
				return
			handle_start_time = time.time()
			new_df = df.iloc[start_index:]#.copy()
			if new_df.empty:
				Log.w('nothing to process (zero rows) starting from index {}', start_index)
				return
			indices = new_df.index.values #list(range(start_index, len(df)))
			index_count = len(new_df)
			predictors = self.predictors_map[jobuid]
			Log.d('feeding indices, epochs [{}..{}] ({} rows) to {} predictors for key: {}', indices[0], indices[-1], len(indices), len(predictors), jobuid)
			processed_count = 0
			prediction_count = 0
			for epoch, row in new_df.iterrows():
				for predictor in predictors:
					try:
						prediction = predictor.process(epoch, df)
						if prediction is not None:
							col_name = predictor.prefix
							new_df.at[epoch, col_name] = prediction
							prediction_count += 1
							self.print_acc(new_df)
							Log.d('prediction: {}', prediction)
							Log.d('prediction {} received, sleeping..', prediction_count)
							time.sleep(3)
					except Exception as predict_error:
						raise Exception('Failed to feed epoch {} to predictor {}'.format(epoch, type(predictor).__name__))
				processed_count += 1
				if processed_count % int(index_count/10) == 0:
					percentage_processed = 100 * processed_count / index_count
					Log.d('..processed {}/{} {:.1f}%', processed_count, index_count, percentage_processed)
			Log.d('fed predictors on {} new rows (now {} in total) in {:.1f}s', index_count, len(df), time.time() - handle_start_time) 
			try:	
				h5_start_time = time.time()
				with pd.HDFStore(self.h5_out_filepath, mode='a') as h5: 		
					h5.append(jobuid, new_df, format='table', data_columns=True)
					row_count = h5.get_storer(jobuid).nrows
					Log.d('h5 row count is now: {}', row_count)
				Log.d('appended {}/{} rows to hdf5 in {:.1f}s', index_count, len(df), time.time() - h5_start_time) 
			except Exception as h5e:
				raise Exception('Failed to write to hdf file') from h5e
		except Exception as e:
			raise Exception('Failed to handle epoch') from e
		Log.d('finished handling block')
	def print_acc(self, df):
		Log.d('begin acc calc ======')
		y_predict_colname = 'prediction_ensmbl_next_trend_feature' #'prediction_awsdnn_next_trend'
		y_true_colname = 'feature_rtrspc()_next_trend_pricefeature'
		df = df[[y_predict_colname, y_true_colname]]
		filtered = df.dropna(how='any')
		Log.d('acc source frame:\n{}', filtered)
		Log.d('dropped {}/{} rows where either the predictor or the true value was unspecified', len(df) - len(filtered), len(df))
		y_predict = filtered[y_predict_colname]
		y_true = filtered[y_true_colname]
		score = accuracy_score(y_true, y_predict, normalize=True)
		Log.d('accuracy: {}', score)
		Log.d('===== end acc calc ')
	def run_async(self):
		self.h5_watcher.trigger()
		thread = self.h5_watcher.run_async()
		return thread
