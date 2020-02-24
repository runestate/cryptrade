import sys; 
sys.path.append('../fetch')
sys.path.append('../python')
import numpy as np
from db import DatabaseGateway, Datasource, Exchange, Currency
from core import OsExpert, Timespan, AppConfig, StringExpert, version
from app import App
from applogging import Log
import time
from collections import deque, namedtuple
import pandas as pd
from datetime import datetime
from interval_stat import IntervalStat
from matplotlib.finance import candlestick_ohlc
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from os import path 
from hodrick_prescott_feature import HodrickPrescottFeature
from candlestick_feature import CandlestickFeature
from passthrough_feature import PassthroughFeature
from generator_job import GeneratorJob
from feature_base import FeatureBase
from exp_moving_average_crossover_agent import ExpMovingAverageCrossOverAgent
from moving_average_crossover_agent import MovingAverageCrossOverAgent
from stochastic_oscillator_agent import StochasticOscillatorAgent
from volume_agent import VolumeAgent
from retrospec_agent import RetroSpecAgent
from linear_gap_resolver import LinearGapResolver
from double_observation_error import DoubleObservationError
import re
from functools import reduce
from itertools import repeat

@version(1,0,0)
class GeneratorApp(App):
	def __init__(self, version):
		super().__init__(__file__)
		self.window_size = 15
		self.interval_seconds = [15 * 60] # 15 minutes
		self.contruct_time = time.time()
		self.version = version
		self.sleep_seconds = 1 # must be low enough to produce empty result set eventually > reaktime
		self.transaction_min_timestamp = int(AppConfig.setting('GENERATOR_TRANSACTION_MIN_TIMESTAMP'))
		self.data_dirpath = AppConfig.setting('GENERATOR_DATA_DIRPATH')
		Log.d('construct: {}', self.__dict__)
		self.db = DatabaseGateway()
		max_history_minutes = 10 * 24 * 60#max(self.minute_intervals)
		self.from_currency_ids = []
		self.to_currency_ids = []
		self.run_config = self.read_run_config()
		self.jobs = list(self.__jobs_iterate(max_history_minutes, self.run_config))
		Log.i('count of generator jobs: {}', len(self.jobs))
	def read_run_config(self):
		with open('generator_config.py', 'r') as config_file:
			return eval(config_file.read())
	def agent_prefix(self, agent_type, agent_params):
		param_tokens =  [
			'{}-{}'.format(
				name.lower().replace('_', ''), 
				str(value).replace('0.', '0')
				)
			for name, value in agent_params.items()
			]
		return 'feature_{}({})_'.format(
			agent_type.NAME, # ''.join(type_tokens),
			'|'.join(param_tokens)
			)
	def explode_args(self, args_dicts): # TODO: convert to yield
		if args_dicts is None or len(args_dicts) == 0:
			return [{}]
		total_results = []
		for args_dict in args_dicts:
			results = []
			for key, values in args_dict.items():
				new_results = []
				for value in values:
					for dict_result in (results if len(results) > 0 else [{}]):
						new_results.append({
							**dict_result,
							key: value
						}) 
				results = new_results
			total_results += results
		return total_results
	def __jobs_iterate(self, frame_history_minutes, run_config): 
		datasources = self.db.datasources()
		exchanges = self.db.exchanges()
		currencies = self.db.currencies()
		real_currencies = [c for c in currencies if c.is_crypto == False]
		crypto_currencies = [c for c in currencies if c.is_crypto == True]
		agents = [
			CandlestickFeature, 
			PassthroughFeature, 
			MovingAverageCrossOverAgent, 
			ExpMovingAverageCrossOverAgent, 
			StochasticOscillatorAgent,
			VolumeAgent,
			HodrickPrescottFeature,
			RetroSpecAgent
			]
		assert all(agent.KEYS.count(key) == 1 for agent in agents for key in agent.KEYS) # ensure agents have no duplicate keys 
		for datasource in [d for d in datasources if d.name in run_config['datasource_name']]:
			for exchange in [e for e in exchanges if e.name in run_config['exchange_name']]:
				for from_currency in [cc for cc in crypto_currencies if cc.code in run_config['from_currency_code']]:#, 'ETH', 'XRP']]:
					self.from_currency_ids.append(from_currency.id)
					for to_currency in [rc for rc in real_currencies if rc.code in run_config['to_currency_code']]:
						self.to_currency_ids.append(to_currency.id)
						for interval_second in self.interval_seconds:
							for agent_name in run_config['agent_config'].keys():
								assert len([a for a in agents if a.__name__ == agent_name]) == 1, 'not exactly one entry for agent name {}'.format(agent_name)
							yield GeneratorJob(
								datasource = datasource,
								exchange = exchange,
								from_currency = from_currency,
								to_currency = to_currency,
								interval_second = interval_second,  #[5*60, 15*60, 30*60, 3600, 3600*12] 
								features = [
									self.create_agent(agent_type, exploded_agent_params)
									for agent_type in agents 
									for config_agent_name, config_agent_params in run_config['agent_config'].items()
									for exploded_agent_params in self.explode_args(config_agent_params)
									if  agent_type.__name__ == config_agent_name
									],
								uid='{}_{}_{}_{}_{}'.format(datasource.name, exchange.name, from_currency.code, to_currency.code, interval_second)
								)
	def create_agent(self, agent_type, args):
		Log.d('creating agent {} with args: {}', agent_type.__name__, args)
		return agent_type(
			col_prefix=self.agent_prefix(agent_type, args), 
			**args
			) 		
	def feed_jobs_forever(self, job_changed_handler):	
		assert job_changed_handler is not None
		sleep_seconds = self.sleep_seconds
		transaction_min_timestamp = self.transaction_min_timestamp 
		start_transaction_min_timestamp = transaction_min_timestamp
		data_dirpath = self.data_dirpath
		start_time = time.time()	
		Log.i('processing transactions, sleep interval {}s, starting from epoch {} ({})', sleep_seconds, transaction_min_timestamp, StringExpert.format_timestamp(transaction_min_timestamp))
		to_fetch_count = self.db.transaction_count(transaction_min_timestamp)
		Log.d('transaction count since {} ({}): {}', transaction_min_timestamp, StringExpert.format_timestamp(transaction_min_timestamp), to_fetch_count)
		pd.set_option('io.hdf.default_format','table')
		hdf5_filename = '{}_{}_{}.h5'.format(
			self.version.major, 
			self.version.minor, 
			datetime.fromtimestamp(start_time).strftime('%Y%m%d_%H%M%S')
			)
		hdf5_filepath = path.join(data_dirpath, hdf5_filename)
		Log.i('hdf5 output filepath is: \n{}', hdf5_filepath)
		set_size = 1000
		fetch_count = 0
		plot_time = time.time()
		is_realtime = False
		while True:
			try:
				next_transaction_min_timestamp = self.process_transaction_subset(transaction_min_timestamp, set_size, hdf5_filepath, job_changed_handler, is_realtime)
				if next_transaction_min_timestamp is None:
					Log.d('nothing to process, waiting..')
					is_realtime = True # TODO: empty polling perhaps not the best indicator of switch to realtime
					time.sleep(sleep_seconds)
				else:
					assert next_transaction_min_timestamp > transaction_min_timestamp, 'next minimum timestamp was not greater than the current timestamp'
					transaction_min_timestamp = next_transaction_min_timestamp
					fetch_count += set_size
					percentage = 100*fetch_count/to_fetch_count
					current_time = time.time()
					Log.d('processed {}/{}, {}%, spent {} on the period {} ({}) to {} ({})', 
						fetch_count, 
						to_fetch_count, 
						int(percentage), 
						Timespan.from_seconds(int(current_time - start_time)).as_string(),
						StringExpert.format_timestamp(start_transaction_min_timestamp),
						start_transaction_min_timestamp,
						StringExpert.format_timestamp(transaction_min_timestamp),
						transaction_min_timestamp
						)
			except Exception as e:
				raise Exception('Failed to process nonparsed api responses') from e
		Log.w('all {} rows read, but should loop forever', row_count) 
	def process_transaction_subset(self, transaction_min_timestamp, set_size, hdf5_filepath, job_changed_handler, is_realtime):
		assert job_changed_handler is not None, 'no job_changed_handler provided'
		window_size = 10
		subset_process_start_time = time.time()
		frame = self.db.transaction_by_timestamp_frame(
			transaction_min_timestamp, 
			set_size, 
			self.from_currency_ids, 
			self.to_currency_ids
			)
		frame.set_index('epoch_time', inplace=True)
		row_count = frame.shape[0]
		Log.d('...time spent fetching subset ({} rows) from db: {:.2f}s', row_count, time.time() - subset_process_start_time)
		if row_count == 0:
			return None
		row_process_count = 0
		last_epoch_time = None
		Log.d('...processing rows...')
		row_process_start_time = time.time()
		gap_resolver = self.run_config['gap_resolver']
		for epoch_time, row in frame.iterrows():
			is_row_processed = False
			try:
				transaction_id   = row['id'] 
				datasource_id    = row['datasource_id']
				exchange_id      = row['exchange_id']
				from_currency_id = row['from_currency_id']
				to_currency_id   = row['to_currency_id']
				price 			 = np.float64(row['price'])
				volume 			 = np.float64(row['volume'])
				transaction_min_timestamp = epoch_time #transaction_id + 1
				seconds_since_previous = 0 if last_epoch_time is None else epoch_time - last_epoch_time
				Log.t('seconds since previous epoch time: {}', seconds_since_previous)	
				if last_epoch_time is not None:
					assert epoch_time >= last_epoch_time, 'epoch time ({}) was less than the previous epoch time ({})'.format(epoch_time, last_epoch_time)
				
				seconds_since_previous = 0 if last_epoch_time is None else epoch_time - last_epoch_time
				assert seconds_since_previous >= 0, 'seconds_since_previous cannot be a negative value'
				last_epoch_time = epoch_time
				for job in self.jobs:
					if (
						job.datasource.id == datasource_id and 
						job.exchange.id == exchange_id and 
						job.from_currency.id == from_currency_id and 
						job.to_currency.id == to_currency_id
						):
						is_row_processed = True							
						try:
							h5frame = job.frame 
							if h5frame is not None: # perfrom integrity check on existing =  non-empty dataframe
								assert not h5frame.empty # should not be possible if the frame has previously been created
								last_epoch = h5frame.index.values[-1]
								seconds_since_previous = epoch_time - last_epoch
								assert seconds_since_previous >= 0
								max_gap_seconds = 120# TODO make config setting
								if (seconds_since_previous > max_gap_seconds): # TODO make config setting
									warn_message = 'excessive time (+{}s) passed since previous observation: {}s ({}) between {} ({}) and {} ({})'.format( 
										max_gap_seconds,
										seconds_since_previous,
										Timespan.from_seconds(int(seconds_since_previous)).as_string(), 
										last_epoch,
										StringExpert.format_timestamp(last_epoch),
										epoch_time,
										StringExpert.format_timestamp(epoch_time)
										)
									if gap_resolver is None:
										raise Exception(warn_message)
									Log.w(warn_message)
									prev_observation = h5frame.iloc[-1]
									df_intermediates = gap_resolver.intermediates_frame(
										max_gap_seconds,
										from_epoch=last_epoch, to_epoch=epoch_time,
										from_price=prev_observation['latest'], to_price=price,
										from_volume=prev_observation['volume'], to_volume=volume
										)
									Log.d('simulating intermediate observations:\n{}', df_intermediates)
									simulated_count = 0
									for intermediate_epoch, intermediate in df_intermediates.iterrows():
										job_observation= job.job_observe(
											value=intermediate['price'], 
											epoch_time=intermediate_epoch, 
											volume=intermediate['volume'],
											is_simulated=True,
											is_realtime=False
											)
										assert job_observation is not None
										simulated_count += 1
										if simulated_count % 1000 == 0:
											Log.d('..simulated {}/{}..', simulated_count, len(df_intermediates))
									Log.i('done simulating {} observations up until epoch {} ({})', len(df_intermediates), epoch_time, StringExpert.format_timestamp(epoch_time))
							try:								
								job_observation = job.job_observe(
									value=price, 
									epoch_time=epoch_time, 
									volume=volume,
									is_simulated=False,
									is_realtime=is_realtime)
								row  = job_observation# job_observation_to_frame_row(volume, job_observation)
								assert row is not None
								job_changed_handler(job)
							except DoubleObservationError as doe:
								Log.w('epoch already in frame, will be ignored ({})', epoch_time)	
						except Exception as job_e:
							raise Exception('Failed to feed row to job') from job_e
			except Exception as e:
				raise Exception('Failed to process row index {}'.format(epoch_time)) from e
			if is_row_processed:
				row_process_count += 1
		Log.d('...time spent processing {}/{} rows in time: {:.2f}s', row_process_count, frame.shape[0], time.time() - row_process_start_time)		
		with pd.HDFStore(hdf5_filepath, mode='a') as h5: 		
			h5_process_start_time = time.time()
			start_observation_epoch = frame.index.values[0]			
			for job in self.jobs:
				df_to_append = job.frame[job.frame.index >= start_observation_epoch]
				try:
					h5.append(job.uid, df_to_append, format='table', data_columns=True)
					row_count = h5.get_storer(job.uid).nrows
					Log.d('...h5 key {}, row count is {}', job.uid, row_count)
				except Exception as append_error:
					raise append_error
		Log.d('...time spent adding to h5: {:.2f}s', time.time() - h5_process_start_time)		
		row_processing_time = time.time() - subset_process_start_time
		Log.d('...total time spent on subset: {:.2f}s ({:.2f}s per row)', row_processing_time, row_processing_time / row_process_count )
		return transaction_min_timestamp
if __name__ == '__main__':
	file_dirpath = OsExpert.path_backstep(__file__)
	pd.options.display.float_format = '{:.2f}'.format
	try:
		app = GeneratorApp()
		app.feed_jobs_forever(
			job_changed_handler=lambda job: None#Log.w('dummy callback for job: {}', job.uid)
			)
	except KeyboardInterrupt:
		print('\n\nKeyboardInterrupt\n')
	except Exception as e:
		Log.c('app failed: {}', e)
		stacktrace = OsExpert.stacktrace()
		Log.d('stacktrace:\n{}', stacktrace)
