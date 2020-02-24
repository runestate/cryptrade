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
from numpy import float64, nan
from action_feature import ActionFeature
from feature_base import FeatureBase
from downtrend_reversal_pattern import DowntrendReversalPattern
from uptrend_reversal_pattern import UptrendReversalPattern
from candlestick_pattern import CandlestickPattern

color_up_hex = 0x9BC441
color_down_hex = 0xFC1368
def slightly_darker(hex):
	return ((hex & 0x7E7E7E) >> 1) | (hex & 0x808080)
color_up = '#{:x}'.format(color_up_hex)
color_down = '#{:x}'.format(color_down_hex)
down_reversal_pattern_color = '#{:x}'.format(slightly_darker(color_up_hex)) # darken color
up_reversal_pattern_color = '#{:x}'.format(slightly_darker(color_down_hex)) # lighter: 0x7f7f7f
dfkeys = ['open', 'high', 'low', 'close', 'interval_begin_epoch_time']
down_reversal_cf = 'down_reversal_{}'.format(CandlestickPattern.__name__).lower()
up_reversal_cf = 'up_reversal_{}'.format(CandlestickPattern.__name__).lower()
action_cf = 'action_{}'.format(ActionFeature.__name__).lower()

class CandlestickFeature(FeatureBase):
	NAME='cdlstk'	
	KEYS=['is_white', 'is_black', 'body', 'upper_shadow', 'lower_shadow', down_reversal_cf, up_reversal_cf, action_cf, 'active']
	def __init__(self, col_prefix, tag=None):
		Log.t('construct')
		super().__init__(tag)
		self.col_prefix = col_prefix
	def feature_observe(self, epoch_time, interval_value, history_frame, is_first_value_in_interval, is_reset_observation): 
		t_result = history_frame.iloc[-1] # get the last row in the completed interval
		
		t_high = t_result.high
		t_low = t_result.low
		t_open = t_result.open
		t_close = t_result.close
		t_active = 1
		t_range = t_high - t_low
		t_is_white = t_close > t_open
		t_is_black = t_close < t_open
		t_body = 0 if t_range == 0 else abs(t_close - t_open) / t_range
		t_upper_shadow = 0 if t_range == 0 else (t_high - max(t_open, t_close)) / t_range
		t_lower_shadow = 0 if t_range == 0 else (min(t_close, t_open) - t_low)  / t_range
		assert t_range >= 0
		assert t_upper_shadow >= 0
		assert t_lower_shadow >= 0
		t_result = {
			'active': 1,
			'is_white': float64(t_is_white), 
			'is_black': float64(t_is_black), 
			'body': t_body, 
			'upper_shadow': t_upper_shadow, 
			'lower_shadow': t_lower_shadow, 
			action_cf: ActionFeature.HOLD
		}
		if is_first_value_in_interval is True:
			grouped = history_frame[history_frame['is_closing'] == 1]
			cp = self.col_prefix
			grouped.rename(columns=lambda c: c if not c.startswith(cp) else c[len(cp):], inplace=True)
			if len(grouped) >= 3:
				t1 = grouped.iloc[-1] # the 2nd most recent must be the last row in the completed interval
				t2 = grouped.iloc[-2] # the 2nd most recent must be the last row in the completed interval
				t3 = grouped.iloc[-3] # the 2nd most recent must be the last row in the completed interval
				down_reversal_pattern = DowntrendReversalPattern.pattern(t1, t2, t3)
				if down_reversal_pattern is not None:
					t_result[down_reversal_cf] = down_reversal_pattern 
					t_result[action_cf] = ActionFeature.BUY
				up_reversal_pattern = UptrendReversalPattern.pattern(t1, t2, t3)
				if up_reversal_pattern is not None:
					t_result[up_reversal_cf] = up_reversal_pattern
					t_result[action_cf] = ActionFeature.SELL
		return t_result
	@staticmethod
	def annotation_text(pattern_index):
		pattern_name = str(CandlestickPattern(pattern_index))
		return pattern_name.replace('CandlestickPattern.', '').replace('IS_', '')
	def annotate_reversal_patterns( ax1, frame, value_key, color, y_key, y_offset, arrow_length, curve, min_y, max_y, rotation): 
		for i,r in frame[frame[value_key].notnull()].iterrows():
			h = float(r[y_key])
			epoch_time = mdates.date2num(datetime.fromtimestamp(i))
			pattern = r[value_key]
			ax1.annotate(
				CandlestickFeature.annotation_text(pattern), 
				xy = (epoch_time, h + y_offset), 
				xytext = (epoch_time, min(max_y, max(min_y, (h + y_offset + arrow_length)))), 
				verticalalignment='center', 
				horizontalalignment='center',
				color=color,
				fontsize=11,
				rotation=rotation,
				alpha = .3,
				arrowprops = dict(
					connectionstyle='arc3,rad={}'.format(curve),
					arrowstyle='->'	,
					color=color,
					)
				)
	@staticmethod
	def plot(title, second_count, frame, ax1, is_image, label_connect, filter_in_nth, cp):
		if frame is None or len(frame) < 2:
			return None
		index_min = frame.index[0]
		index_max = frame.index[-1]
		min_timetamp = index_min
		filtered = frame[frame.index >= min_timetamp]
		filtered[cp + down_reversal_cf] = filtered[cp + down_reversal_cf].shift(-1)
		filtered[cp + up_reversal_cf] = filtered[cp + up_reversal_cf].shift(-1)
		grouped = filtered.groupby('interval_begin_epoch_time').last()
		if grouped.empty: 
			return None
		values = [
			(	mdates.date2num(datetime.fromtimestamp(i)), 
				r.open, 
				r.high, 
				r.low, 
				r.close
			) 
			for i,r in grouped.iterrows()
			]
		plot = candlestick_ohlc(
			ax1, 
			values, 
			width=15*.6/(24*60), 
			colorup=color_up, 
			colordown=color_down,
			alpha=0.9
			)
		max_y = float(grouped.high.max())
		min_y = float(grouped.low.min())
		arrow_length = 27 if is_image else 1
		arrow_offset = .3
		arc = 0.05
		rotation = 60 if is_image else 90
		CandlestickFeature.annotate_reversal_patterns(ax1, grouped, cp + down_reversal_cf, down_reversal_pattern_color, 'low', -arrow_offset, -arrow_length, arc, min_y, max_y, rotation)
		CandlestickFeature.annotate_reversal_patterns(ax1, grouped, cp + up_reversal_cf, up_reversal_pattern_color, 'high', arrow_offset,  arrow_length, arc, min_y, max_y, rotation)
		return ax1
