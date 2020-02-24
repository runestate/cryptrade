import pandas as pd
from applogging import Log
from feature_base import FeatureBase
from numpy import nan

class PassthroughFeature(FeatureBase):
	NAME='pastrg'
	KEYS=['active']
	def __init__(self, col_prefix, tag=None):
		super().__init__(tag)
		self.col_prefix = col_prefix
		self.value = nan
	def feature_observe(self, epoch_time, interval_value, history_frame, is_first_value_in_interval, is_reset_observation): 
		return { 'active': 1 }
	@staticmethod
	def plot(title, second_count, frame, ax, is_image, label_connect, filter_in_nth, cp):
		values = FeatureBase.derive_plot_values(title, second_count, frame.ix[:,'latest'])
		if values is None:
			return None
		filtered = values[values.index % filter_in_nth == 0]
		ax.plot(
			filtered['index'].tolist(), 
			filtered['latest'].tolist(), 
			color='blue',
			alpha=0.9,
			zorder=-10)
