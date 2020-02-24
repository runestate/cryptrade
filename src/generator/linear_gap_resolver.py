from applogging import Log
from core import AppConfig
import numpy as np
import pandas as pd

class LinearGapResolver:
	@staticmethod
	def intermediates_frame(max_gap_seconds, from_epoch, to_epoch, from_price, to_price, from_volume, to_volume):
		result_frame = pd.DataFrame(columns=['price', 'volume'], index=[], dtype=np.float64)
		fake_epochs = np.arange(from_epoch + max_gap_seconds, to_epoch, max_gap_seconds)
		volume_range = to_volume - from_volume
		price_range = to_price - from_price
		epoch_range = to_epoch - from_epoch
		for fake_epoch in fake_epochs:
			scale = (fake_epoch - from_epoch) / epoch_range
			fake_volume = from_volume + volume_range * scale
			fake_price = from_price + price_range * scale
			result_frame.at[fake_epoch] = { 'price': fake_price, 'volume': fake_volume  }
		return result_frame
			
