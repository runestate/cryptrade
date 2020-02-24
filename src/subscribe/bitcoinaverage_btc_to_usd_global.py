from .BitcoinAverageFetcher import *
from core import  Market

class BitCoinAverageBtcToUsdGlobal(BitcoinAverageFetcher):
	def __init__(self):
		super().__init__(__file__, 'BTC', 'USD', Market.Global)
