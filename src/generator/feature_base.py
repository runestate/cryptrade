from db import DatabaseGateway, Datasource, Exchange, Currency
from core import OsExpert, Timespan, AppConfig
from app import App
from applogging import Log
import time
from collections import deque, namedtuple
import pandas as pd
from datetime import datetime
from interval_stat import IntervalStat
from enum import Enum
from matplotlib.finance import candlestick_ohlc
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from os import path 

class FeatureBase:
	def __init__(self, tag=None):
		self.tag = tag 
	@staticmethod
	def derive_plot_values(title, second_count, frame):
		index_max = frame.index.max()
		index_min = frame.index.min()
		min_timetamp = index_min if second_count == None else index_max - second_count
		values = frame[frame.index >= min_timetamp].reset_index().astype(float)
		frame_span_seconds = (index_max - index_min)
		if values.empty or (second_count != None and frame_span_seconds < second_count):
			return None
		values['index'] = values['index'].map(lambda i: mdates.date2num(datetime.fromtimestamp(i)))
		return values
	def past_time_epoch(self, second_count):
		return int(time.time()) - second_count
