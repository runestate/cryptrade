from applogging import Log
from datetime import datetime
import time
from numpy import float64

class IntervalStat:
	def __init__(self, interval_second, epoch_time):
		self.interval_second = interval_second
		self.reset(epoch_time)
	def reset(self, epoch_time):
		self.low = None
		self.high = None
		self.open = None
		self.close = None
		self.latest = None
		self.is_opening = False
		self.is_closing = False
		self.observation_count = 0
		interval_position_epoch = epoch_time % self.interval_second # find the 'time passed' within the interval
		self.interval_start_epoch = epoch_time - interval_position_epoch
		self.interval_end_epoch = self.interval_start_epoch + self.interval_second
		interval = self.interval_start_epoch / self.interval_second
		assert interval % 1 == 0, 'interval index {} is not an integer'.format(interval)
		self.interval_index = int(interval)
		Log.t(
			self.interval_index,
			datetime.utcfromtimestamp(self.interval_start_epoch),
			datetime.utcfromtimestamp(self.interval_end_epoch)
			)
	def any_observations(self):
		return this.observation_count > 0
	def current_time_epoch(self):
		return int(time.time())
	def interval_observe(self, value, epoch_time):
		assert self.is_closing == False
		if self.low is None or self.low > value:
			self.low = value
		if self.high is None or self.high < value:
			self.high = value
		if self.open is None:
			self.open = value
		self.close = value
		self.latest = value
		self.is_opening = 1 if self.observation_count == 0 else 0
		self.observation_count += 1
	def as_dict(self): # TODO: use __dict__
		return {
			'open': self.open, 
			'high': self.high, 
			'low': self.low, 
			'close': self.close,
			'latest': self.latest,
			'interval_begin_epoch_time': self.interval_start_epoch,
			'is_opening': float64(self.is_opening),
			'is_closing': float64(self.is_closing)
		}
