from db import DatabaseGateway, Datasource, Exchange, Currency
from core import OsExpert, Timespan, AppConfig, StringExpert
from app import App
from applogging import Log
import time
from collections import deque, namedtuple
import pandas as pd
from datetime import datetime
from interval_stat import IntervalStat
from os import path 
from numpy import float64, nan
from double_observation_error import DoubleObservationError
import numpy as np

class GeneratorJob:
	def __init__(self, 		
		datasource, 
		exchange,	
		from_currency,
		to_currency,
		interval_second,
		features,
		uid
		):
		assert isinstance(datasource, Datasource)
		assert isinstance(exchange, Exchange)
		assert isinstance(from_currency, Currency)
		assert isinstance(to_currency, Currency)
		assert isinstance(features, list)
		assert isinstance(interval_second, int)
		self.datasource = datasource 
		self.exchange = exchange
		self.from_currency = from_currency
		self.to_currency = to_currency
		self.features = features # trend agent must be first!
		self.interval_second = interval_second
		self.uid = uid
		self.frame = None
		self.interval_stat = None
		self.reserved_cols = ['time', 'volume', 'age', 'is_simulated', 'is_realtime']
		self.feature_reserved_cols = ['time']
		Log.d('generator job created with features: {}', sorted([f.col_prefix for f in self.features]))
	def emptyFrame(self, istat):
		keys = (
			self.reserved_cols +			
			list(self.interval_stat.as_dict().keys()) + # TODO: too complicated, simplify
			[ f.col_prefix + fk for f in self.features for fk in self.feature_reserved_cols ] + 
			[ f.col_prefix + fk for f in self.features for fk in f.KEYS ] 
			)
		return pd.DataFrame(columns=keys, dtype=float64)
	def job_observe(self, value, epoch_time, volume, is_simulated, is_realtime):
		if self.interval_stat is None:
			self.interval_stat = IntervalStat(self.interval_second, epoch_time)
		if self.frame is None: # TODO: must to constructor
			self.frame = self.emptyFrame(self.interval_stat)
		istat = self.interval_stat
		if epoch_time in self.frame.index:
			raise DoubleObservationError(epoch_time)
		is_first_value_in_interval = epoch_time >= istat.interval_end_epoch
		if is_first_value_in_interval:
			self.frame.iloc[-1, self.frame.columns.get_loc('is_closing')] = 1	
			istat.reset(epoch_time)	
		istat.interval_observe(value=value, epoch_time=epoch_time)
		interval_value = istat.as_dict()
		assert volume is not None
		assert isinstance(volume, np.float64)
		self.frame.at[epoch_time] = {
			**interval_value,
			'volume': volume,
			'age': 0 if self.frame.empty else epoch_time - self.frame.index.values[0],
			'is_simulated': 1 if is_simulated is True else 0,
			'is_realtime': 1 if is_realtime is True else 0
			}
		total_time_spent = 0
		for f in self.features:
			try:
				start_time = time.time()
				feature_observation = f.feature_observe(
					epoch_time=epoch_time, 
					interval_value=interval_value, 
					history_frame=self.frame,
					is_first_value_in_interval=is_first_value_in_interval,
					is_reset_observation=False
					) 				
				time_spent = time.time() - start_time 
				self.frame.at[epoch_time, f.col_prefix + 'time'] = time_spent					
				if feature_observation is not None:
					assert isinstance(feature_observation, pd.Series) or isinstance(feature_observation, dict) 
					kv_pairs = feature_observation.iteritems() if isinstance(feature_observation, pd.Series) else feature_observation.items()
					for key, value in kv_pairs:
						if value is None:
							Log.w('feature agent returned the None value for job uid {}, feature {} and pair key {}', self.uid, f.NAME, key)
						elif value is not nan:
							colname = f.col_prefix + key
							assert colname in self.frame
							self.frame.at[epoch_time, colname] = value		
				total_time_spent += time_spent			
			except Exception as e:
				raise Exception('Failed to feed value to feature "{}"'.format(f.col_prefix))
			self.frame.at[epoch_time, 'time'] = total_time_spent					
		if len(self.frame) % 500 == 0:
			self.print_stats()
		return self.frame.loc[epoch_time]
	def print_stats(self):
		stats = self.frame[[f.col_prefix + 'time' for f in self.features]].sum()
		Log.d('time stats: \n{}', stats)
	def observation_count(self):
		return len(self.frame)
