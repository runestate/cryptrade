import pandas as pd
from applogging import Log
from feature_base import FeatureBase
from action_feature import ActionFeature
from numpy import nan
from core import StringExpert

upper_k = .8
lower_k = .2
action_cf = 'action_{}'.format(ActionFeature.__name__).lower()

class StochasticOscillatorAgent(FeatureBase): 
	NAME='stcosc'
	KEYS=['k', 'd_fast', 'd_slow', action_cf, 'active']
	def __init__(self, col_prefix, period_seconds, tag=None):
		super().__init__(tag)
		self.col_prefix = col_prefix
		self.period_seconds = period_seconds
		self.signal_period_seconds = period_seconds * 0.2 # TODO: should be a parameter? 
		assert self.period_seconds > self.signal_period_seconds
	def feature_observe(self, epoch_time, interval_value, history_frame, is_first_value_in_interval, is_reset_observation): 
		cp = self.col_prefix
		period_min_epoch = epoch_time - self.period_seconds
		if history_frame[history_frame.index < period_min_epoch].empty:
			return { 'active': 0 }
		period_df = history_frame[history_frame.index >= period_min_epoch]
		assert len(period_df) > 1
		period_latest_ser = period_df['latest']
		c_t = period_latest_ser.iloc[-1] #history_frame.loc[epoch_time]['latest']
		l_n = period_latest_ser.min()
		h_n = period_latest_ser.max()
		k = (c_t - l_n) / (h_n - l_n)
		history_frame.at[epoch_time, cp + 'k'] = k
		
		d_signal_min_epoch = epoch_time - self.signal_period_seconds
		d_fast_df = history_frame[history_frame.index >= d_signal_min_epoch]
		assert len(d_fast_df) > 0
		d_fast = d_fast_df[cp + 'k'].mean()
		history_frame.at[epoch_time, cp + 'd_fast'] = d_fast
		d_slow_df = history_frame[history_frame.index >= d_signal_min_epoch] # TODO: optimize, i.e. don't select subsets multiple times
		assert len(d_slow_df) > 0
		d_slow = d_slow_df[cp + 'd_fast'].mean()
		history_frame.at[epoch_time, cp + 'd_slow'] = d_slow		
		prev_k = history_frame.iloc[-2][cp + 'k'] # TODO: optimize
		prev_d_slow = history_frame.iloc[-2][cp + 'd_slow']
		action = (
			ActionFeature.BUY  if prev_k < prev_d_slow < lower_k and d_slow < k < lower_k else
			ActionFeature.SELL if prev_k > prev_d_slow > upper_k and d_slow > k > upper_k else
			ActionFeature.HOLD
			)
		return { 
				'active': 1,
				action_cf: action
			}
	@staticmethod
	def plot(title, second_count, frame, ax, is_image, label_connect, filter_in_nth, cp):
		values = FeatureBase.derive_plot_values(title, second_count, frame)
		if values is None:
			return None
		latest_min = values['latest'].min()
		mult_factor = values['latest'].max() - latest_min
		offset_y = (latest_min - mult_factor)
		values[cp + 'd_slow'] = values[cp + 'd_slow'] * mult_factor + offset_y
		values[cp + 'd_fast'] = values[cp + 'd_fast'] * mult_factor + offset_y
		values[cp + 'k'] = values[cp + 'k'] * mult_factor + offset_y
		filtered = values[values.index % filter_in_nth == 0]
		assert len(filtered) > 0
		Log.d(frame[cp + action_cf].value_counts())
		indices = filtered['index'].tolist()
		df_k = filtered[cp + 'k']
		ax.plot(
			indices, 
			df_k, 
			color='orange',
			alpha=0.9,
			zorder=-5
			)
		df_d_slow = filtered[cp + 'd_slow']
		ax.plot(
			indices, 
			df_d_slow,  
			color='lightblue',
			alpha=0.9
			)
		for y in [0, lower_k, upper_k, 1]:
			ax.plot(
				[indices[0], indices[-1]],
				[ y * mult_factor + offset_y] * 2,
				color='white',
				dashes=[6, 2],
				alpha=0.5,
				zorder=-10
				)
		df_buy = values[values[cp + action_cf] == ActionFeature.BUY]
		ax.scatter(
			df_buy['index'], 
			df_buy[cp + 'd_slow'], 
			color='green',
			s=70,
			zorder=10,
			alpha=0.7
			)
		df_sell = values[values[cp + action_cf] == ActionFeature.SELL]
		ax.scatter(
			df_sell['index'], 
			df_sell[cp + 'd_slow'], 
			color='red',
			s=70,
			zorder=10,
			alpha=0.7
			)
