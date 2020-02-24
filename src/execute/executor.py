import sys; 
sys.path.append('../generator')
sys.path.append('../python')
from db import DatabaseGateway, Datasource, Exchange, Currency
from core import OsExpert, Timespan, AppConfig, StringExpert, version, H5FileWatcher
from app import App
from applogging import Log
import time
from collections import deque, namedtuple
import pandas as pd
from datetime import datetime
from os import path 
from feature_value import FeatureValue
from pathlib import Path
import os
import sys
from generator_app import GeneratorApp
from numpy import nan, isnan, float64

PREDICT_ACTION = 'predict_action'

class Executor:
	def __init__(self, h5_filepath, initial_capital, initial_coins):
		self.h5_watcher = H5FileWatcher(h5_filepath, self.handle_job_epoch)
		self.capital = float64(initial_capital)
		self.initial_capital = self.capital
		self.coins = float64( initial_coins)
		self.start_value = None
		self.accumulated_fees = 0
	def run_async(self):
		self.h5_watcher.trigger()
		return self.h5_watcher.run_async()
	def current_value(self, coin_price):
		return (self.coins * coin_price + self.capital)
	def pay_fee(self, amount):
		assert amount > 0
		fee = amount * float64(.25 / 100) 
		assert self.capital >= fee, '{} >= {}'.format(self.capital, fee)
		self.capital -= fee
		self.accumulated_fees += fee
		print('payed fee:', fee)
	def handle_job_epoch(self, jobuid, df, start_index):
		trade_fee = float64(.25 / 100) 
		min_capital = self.initial_capital * trade_fee * 10
		print(start_index)
		print(len(df))
		try:
			assert jobuid == '/bitcoinaverage_multiple_global_ETH_USD_900', 'unexpected job id'
			new_df = df[start_index:]
			for epoch, row in new_df.iterrows():
				action = row[PREDICT_ACTION]
				coin_price = row['close']
				if self.start_value is None:
					self.start_value = self.current_value(coin_price)
				if not isnan(action):
					print('coin price ', coin_price, ', capital ', self.capital)
					if action == FeatureValue.BUY:					
						coin_transaction_count = (1 - trade_fee) * (self.capital - min_capital) / coin_price 
						if coin_transaction_count > 0:
							print('BUYING coins: ', coin_transaction_count)
							cost = coin_transaction_count * coin_price
							fee  = cost * trade_fee
							assert self.capital >= cost + fee, '{} >= {} + {} = {}'.format(self.capital, cost, fee, cost + fee)
							self.capital -= cost
							self.coins += coin_transaction_count
							self.pay_fee(cost)
					elif action == FeatureValue.SELL:
						fee = min(self.coins * coin_price * trade_fee, self.capital)					
						coin_transaction_count = fee / (coin_price * trade_fee)
						if coin_transaction_count > 0 and self.coins >= coin_transaction_count:
							print('SELLING coins: {}'.format(coin_transaction_count))
							gain = coin_transaction_count * coin_price
							self.capital += gain
							self.coins -= coin_transaction_count
							self.pay_fee(gain)	
						else:
							Log.d('NOT ENOUGH COINS TO SELL! {} at {}', coin_transaction_count, fee)		
					net_worth = self.current_value(coin_price)
		except Exception as e:
			raise Exception('Failed to execute on new job epoch') from e
		print(len(df))
		print(df[PREDICT_ACTION].value_counts())
		print('done')
		sys.stdout.flush()
