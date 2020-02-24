import pandas as pd
from applogging import Log
from feature_base import FeatureBase
from price_feature import PriceFeature

next_trend_cf = 'next_trend_{}'.format(PriceFeature.__name__).lower()

class RetroSpecAgent(FeatureBase):
	NAME='rtrspc'
	KEYS=['active',
		next_trend_cf,
		'percentage_price_change_feature',
		'relative_price_change_feature',
		'percentage_vol_change_feature',
		'relative_vol_change_feature'
		]
	def __init__(self, col_prefix, tag=None):
		super().__init__(tag)
		self.col_prefix = col_prefix
	def feature_observe(self, epoch_time, interval_value, history_frame, is_first_value_in_interval, is_reset_observation): 
		if len(history_frame) < 2:
			return { 'active': 0 }
		prev_price = history_frame['latest'].iat[-2]
		curr_price = history_frame['latest'].iat[-1]
		current_trend = (
			PriceFeature.UPTREND  if prev_price < curr_price else
			PriceFeature.DOWNTREND if prev_price > curr_price else
			PriceFeature.NOTREND
			)
		prev_epoch = history_frame.index.values[-2]
		assert prev_epoch < epoch_time
		history_frame.at[prev_epoch, self.col_prefix + next_trend_cf] = current_trend
		volume = history_frame['volume']
		prev_vol = volume.iat[-2]
		curr_vol = volume.iat[-1]
		return { 
			'active': 1,
			'percentage_price_change_feature': curr_price / prev_price,
			'relative_price_change_feature'  : curr_price - prev_price,
			'percentage_vol_change_feature'  : curr_vol / prev_vol,
			'relative_vol_change_feature'    : curr_vol - prev_vol
		}
	@staticmethod
	def plot(title, second_count, frame, ax, is_image, label_connect, filter_in_nth, cp):
		return None
