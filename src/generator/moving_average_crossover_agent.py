import pandas as pd
from applogging import Log
from feature_base import FeatureBase
from price_feature import PriceFeature
from action_feature import ActionFeature
from numpy import nan
from core import StringExpert
import mpld3

action_cf = 'action_{}'.format(ActionFeature.__name__).lower()
trend_cf = 'trend_{}'.format(PriceFeature.__name__).lower()

class MovingAverageCrossOverAgent(FeatureBase): 
	NAME='movavgcrs'
	KEYS=['slow_avg', 'fast_avg', trend_cf, action_cf, 'active']
	def __init__(self, col_prefix, slow_avg_seconds, fast_avg_seconds, tag=None):
		super().__init__(tag)
		assert slow_avg_seconds > 1, 'cannot average over a single element'
		assert slow_avg_seconds > fast_avg_seconds
		self.col_prefix = col_prefix
		self.slow_avg_seconds = slow_avg_seconds
		self.fast_avg_seconds = fast_avg_seconds
		self.slow_series_to_value = self.frame_to_value
		self.fast_series_to_value = self.frame_to_value
	def frame_to_value(self, series):
		return series.mean()
	def feature_observe(self, epoch_time, interval_value, history_frame, is_first_value_in_interval, is_reset_observation): 
		cp = self.col_prefix
		slow_start_epoch = epoch_time - self.slow_avg_seconds
		fast_start_epoch = epoch_time - self.fast_avg_seconds
		if history_frame.index[history_frame.index < slow_start_epoch].empty: # i.e. there has to be data older  than the slow moving window
			return { 'active': 0 }
		slow_df = history_frame[history_frame.index >= slow_start_epoch]
		fast_df = history_frame[history_frame.index >= fast_start_epoch]
		assert not slow_df.empty
		assert not fast_df.empty
		assert len(slow_df) > len(fast_df), '{} > {}'.format(len(slow_df), len(fast_df))
		slow_avg = self.slow_series_to_value(slow_df['latest'])
		fast_avg = self.fast_series_to_value(fast_df['latest'])
		trend = (
			PriceFeature.UPTREND if fast_avg > slow_avg else 
			PriceFeature.DOWNTREND if fast_avg < slow_avg else
			PriceFeature.NOTREND 
			)
		assert len(history_frame) > 1
		prev_trend = history_frame[cp + trend_cf].iloc[-2]
		action = (
			nan if prev_trend == None else
			ActionFeature.BUY if prev_trend != PriceFeature.UPTREND and trend == PriceFeature.UPTREND else
			ActionFeature.SELL if prev_trend != PriceFeature.DOWNTREND and trend == PriceFeature.DOWNTREND else
			ActionFeature.HOLD 
			)
		return { 
				'slow_avg' : slow_avg,
				'fast_avg' : fast_avg,
				trend_cf : trend,
				action_cf: action,
				'active'   : 1
			}
	@staticmethod
	def plot(title, second_count, frame, ax, is_image, label_connect, filter_in_nth, cp, plot_color_fast = 'gold', plot_color_slow = 'sienna'):
		values = FeatureBase.derive_plot_values(title, second_count, frame[[cp + 'slow_avg', cp + 'fast_avg', cp + action_cf]])
		if values is None:
			return None
		filtered = values[values.index % filter_in_nth == 0]
		indices = filtered['index'].tolist()
		df_slow_avg = filtered[cp + 'slow_avg']
		ax.plot(
			indices, 
			df_slow_avg, 
			color=plot_color_slow,
			alpha=0.9
			)
		df_fast_avg = filtered[cp + 'fast_avg']
		ax.plot(
			indices, 
			df_fast_avg, 
			color=plot_color_fast,
			alpha=0.9
			)
		
		df_buy = values[values[cp + action_cf] == ActionFeature.BUY]
		df_buy_y = df_buy[cp + 'fast_avg'].tolist()
		buy_scatter = plot = ax.scatter(
			df_buy['index'], 
			df_buy_y, 
			color='green',
			s=70,
			alpha=0.7,
			zorder=10
			)
		label_connect(buy_scatter, df_buy_y, color='green')
		df_sell = values[values[cp + action_cf] == ActionFeature.SELL]
		df_sell_y = df_sell[cp + 'fast_avg'].tolist()
		df_sell_scatter = ax.scatter(
			df_sell['index'], 
			df_sell_y, 
			color='red',
			s=70,
			alpha=0.7,
			zorder=10
			)
		label_connect(df_sell_scatter, df_sell_y, color='red')
	
