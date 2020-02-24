from .bitcoinaverage_btc_to_usd_global import *
from .bitcoinaverage_eth_to_usd_global import *
from .bitcoinaverage_xrp_to_usd_global import *
def all():
	return [
		BitCoinAverageBtcToUsdGlobal(), 
		BitCoinAverageEthToUsdGlobal(),
		BitCoinAverageXrpToUsdGlobal()
		]
