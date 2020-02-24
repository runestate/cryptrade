import pandas as pd
from applogging import Log
from feature_base import FeatureBase
from volume_feature import VolumeFeature
from numpy import nan
from core import StringExpert
import mpld3
trend_cf = 'trend_{}'.format(VolumeFeature.__name__).lower()
class VolumeAgent(FeatureBase): 
	NAME='vol'
	KEYS=[trend_cf, 'slow_avg', 'fast_avg', 'active']
	def __init__(self, col_prefix, slow_avg_seconds, fast_avg_seconds, tag=None):
		super().__init__(tag)
		self.col_prefix = col_prefix
		assert slow_avg_seconds > 1, 'cannot average over a single element'
		assert slow_avg_seconds > fast_avg_seconds
		self.slow_avg_seconds = slow_avg_seconds
		self.fast_avg_seconds = fast_avg_seconds
	def feature_observe(self, epoch_time, interval_value, history_frame, is_first_value_in_interval, is_reset_observation): 
		cp = self.col_prefix
		assert cp != ''
		slow_start_epoch = epoch_time - self.slow_avg_seconds
		if history_frame[history_frame.index < slow_start_epoch].empty:
			return { 'active': 0 }
		assert len(history_frame) > 1
		slow_df = history_frame[history_frame.index >= slow_start_epoch]
		fast_start_epoch = epoch_time - self.fast_avg_seconds
		fast_df = slow_df[slow_df.index >= fast_start_epoch]
		assert len(slow_df) > len(fast_df), '{} > {}'.format(len(slow_df), len(fast_df))
		slow_avg = slow_df['volume'].mean()
		fast_avg = fast_df['volume'].mean()
		trend = (
			VolumeFeature.STRONG_VOLUME if fast_avg > slow_avg else 
			VolumeFeature.WEAK_VOLUME 
			)
		return { 
			trend_cf: trend,
			'slow_avg': slow_avg,
			'fast_avg': fast_avg,
			'active': 1
		}
	@staticmethod
	def plot(title, second_count, frame, ax, is_image, label_connect, filter_in_nth, cp):
		trend_col = cp + trend_cf
		values = FeatureBase.derive_plot_values(title, second_count, frame[[cp + 'slow_avg', cp + 'fast_avg', trend_col]])
		if values is None:
			return None
		assert not values.empty
		
		
		df_trend_shift = values[~(values[trend_col] == values[trend_col].shift(-1))][:-1]
		assert not df_trend_shift.empty
		df_strongvol = df_trend_shift[df_trend_shift[trend_col] == VolumeFeature.STRONG_VOLUME] #.drop_duplicates(trend_col)
		assert not df_strongvol.empty
		strongvol_y = df_strongvol[cp + 'fast_avg'].tolist()
		strongvol_scatter = plot = ax.scatter(
			df_strongvol['index'].tolist(), 
			strongvol_y, 
			color='green',
			s=70,
			alpha=0.7,
			zorder=10
			)
		label_connect(strongvol_scatter, strongvol_y, color='green')
		df_weakvol = df_trend_shift[df_trend_shift[trend_col] == VolumeFeature.WEAK_VOLUME]
		assert not df_weakvol.empty
		strongvol_y = df_weakvol[cp + 'fast_avg'].tolist()
		weakvol_scatter = ax.scatter(
			df_weakvol['index'].tolist(), 
			strongvol_y, 
			color='red',
			s=70,
			alpha=0.7,
			zorder=10
			)		
		label_connect(weakvol_scatter, strongvol_y, color='red')
		filtered = values[values.index % filter_in_nth == 0]
		indices = filtered['index'].tolist()
		df_slow_avg = filtered[cp + 'slow_avg']
		ax.plot(
			indices, 
			df_slow_avg, 
			color='pink',
			alpha=0.9
			)
		df_fast_avg = filtered[cp + 'fast_avg']
		ax.plot(
			indices, 
			df_fast_avg, 
			color='violet',
			alpha=0.9
			)
		
	
