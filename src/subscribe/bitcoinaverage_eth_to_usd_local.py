import sys; sys.path.append('..')
import os
from bitcoinaverage import BitcoinAverage, Market
from applogging import Log

class BitCoinAverageEthToUsdLocal(BitcoinAverage):
	def __init__(self):
		Log.d('construct')
		self.file_path = os.path.realpath(__file__)
	async def subscribe(self):
		Log.d('invoked')
		async for result in self.handler_subscribe(self.file_path, 'ETH', 'USD', Market.Local):
			yield result
