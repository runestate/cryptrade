import pandas as pd
from applogging import Log
from feature_base import FeatureBase
from numpy import nan
from core import StringExpert
from moving_average_crossover_agent import MovingAverageCrossOverAgent
from functools import reduce

class ExpMovingAverageCrossOverAgent(MovingAverageCrossOverAgent): 
	NAME='expmovavgcrs'
	def __init__(self, col_prefix, slow_avg_seconds, fast_avg_seconds, slow_alpha, fast_alpha, tag=None):
		super().__init__(col_prefix, slow_avg_seconds, fast_avg_seconds, tag)
		assert 0 <= slow_alpha < fast_alpha <= 1, ' 0 <= {} < {} <= 1'.format(slow_alpha, fast_alpha)
		self.slow_alpha = slow_alpha 
		self.fast_alpha = fast_alpha 
		self.slow_series_to_value = lambda series: reduce(self.slow_exp_avg, series.drop(series.index[0]), series.iloc[0])
		self.fast_series_to_value = lambda series: reduce(self.fast_exp_avg, series.drop(series.index[0]), series.iloc[0])
	def slow_exp_avg(self, previous_exp_avg_value, new_value):
		return self.exp_avg(previous_exp_avg_value, new_value, self.slow_alpha)
	def fast_exp_avg(self, previous_exp_avg_value, new_value):
		return self.exp_avg(previous_exp_avg_value, new_value, self.fast_alpha)
	def exp_avg(self, previous_exp_avg_value, new_value, alpha):
		return alpha * new_value + (1 - alpha) * previous_exp_avg_value;			
	@staticmethod
	def plot(*args, **kwargs):
		MovingAverageCrossOverAgent.plot(*args, **kwargs, plot_color_fast = 'deepskyblue', plot_color_slow = 'darkorchid')
