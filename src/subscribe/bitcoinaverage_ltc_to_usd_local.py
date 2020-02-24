import sys; sys.path.append('..')
import os
from bitcoinaverage import BitcoinAverage, Market
from applogging import Log

class BitCoinAverageLtcToUsdLocal(BitcoinAverage):
	def __init__(self):
		super().__init__()
		Log.d('construct')
		self.file_path = os.path.realpath(__file__)
	async def subscribe(self):
		Log.d('invoked')
		async for result in self.handler_subscribe(self.file_path, 'LTC', 'USD', Market.Local):
			yield result
