from .BitcoinAverageFetcher import *
from core import  Market

class BitCoinAverageEthToUsdGlobal(BitcoinAverageFetcher):
	def __init__(self):
		super().__init__(__file__, 'ETH', 'USD', Market.Global)
