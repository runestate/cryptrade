from .BitcoinAverageFetcher import *
from core import  Market

class BitCoinAverageXrpToUsdGlobal(BitcoinAverageFetcher):
	def __init__(self):
		super().__init__(__file__, 'XRP', 'USD', Market.Global)
