import pandas as pd
from applogging import Log
from feature_base import FeatureBase
import matplotlib.pyplot as plt
import statsmodels.api as sm
from price_feature import PriceFeature 
from numpy import nan

trend_cf = 'trend_{}'.format(PriceFeature.__name__).lower()

class HodrickPrescottFeature(FeatureBase):
	NAME='hodpres'
	KEYS=[trend_cf, 'cycle', 'up_tick_value', 'down_tick_value', 'hp_value', 'historical_hp_value', 'active']
	def __init__(self, col_prefix, frame_history_minutes, lamb, tag=None):
		super().__init__(tag)
		self.lamb = lamb
		self.col_prefix = col_prefix
		self.value = PriceFeature.NOTREND # TODO: remove
	def feature_observe(self, epoch_time, interval_value, history_frame, is_first_value_in_interval, is_reset_observation): 
		cp = self.col_prefix
		if len(history_frame) < 2:
			return { 'active': 0 }
		(cycle, fit) = sm.tsa.filters.hpfilter(history_frame['latest'], lamb=self.lamb) #.astype(float)
		history_frame[cp + 'cycle'] = cycle
		history_frame[cp + 'hp_value'] = fit			
		previous_fitvalue = history_frame[cp + 'historical_hp_value'].iat[-2]
		latest_fitvalue = fit.iloc[-1]
		trend = (
			PriceFeature.UPTREND   if latest_fitvalue > previous_fitvalue else
			PriceFeature.DOWNTREND if latest_fitvalue < previous_fitvalue else 
			PriceFeature.NOTREND
			)
		self.value = trend # important! the agent serves as trend agent for other agents
		return {
				'active': 1,
				trend_cf: trend,	
				'up_tick_value':   latest_fitvalue if trend is PriceFeature.UPTREND   else nan,
				'down_tick_value': latest_fitvalue if trend is PriceFeature.DOWNTREND else nan,
				'historical_hp_value': latest_fitvalue	
			}
	@staticmethod
	def plot(title, second_count, frame, ax, is_image, label_connect, filter_in_nth, cp):
		values = FeatureBase.derive_plot_values(title, second_count, frame).copy()
		if values is None:
			return None
		VAL_COL = 'latest' #cp + 'hp_value'
		CYCLE_COL = cp + 'cycle' # TODO: not historic!
		min_value = values[VAL_COL].min()
		max_cycle = values[CYCLE_COL].max()
		values[CYCLE_COL] = min_value + values[CYCLE_COL] - max_cycle  # make the cycle more visible and prevent it from scaling the graph 
		
		df_ut = values.iloc[values.index % filter_in_nth == 0][['index', cp + 'up_tick_value']].dropna() #.loc[values.shift(-1) != values].dropna()
		ax.scatter(
			df_ut.ix[:,0].tolist(), 
			df_ut.ix[:,1].tolist(), 
			color='green',
			s=0.9
			)
		df_dt = values.iloc[values.index % filter_in_nth == 0][['index', cp + 'down_tick_value']].dropna()
		ax.scatter(
			df_dt.ix[:,0].tolist(), 
			df_dt.ix[:,1].tolist(), 
			color='red',
			s=0.9,
			)
		return ax
