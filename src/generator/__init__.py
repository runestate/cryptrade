from .moving_average_crossover_agent	import MovingAverageCrossOverAgent
from .hodrick_prescott_feature import HodrickPrescottFeature
from .candlestick_feature import CandlestickFeature
from .passthrough_feature import PassthroughFeature
from .stochastic_oscillator_agent import StochasticOscillatorAgent
from .action_feature import ActionFeature
from .candlestick_pattern import CandlestickPattern
from .price_feature import PriceFeature
from .volume_feature import VolumeFeature
from .exp_moving_average_crossover_agent import ExpMovingAverageCrossOverAgent
from .retrospec_agent import RetroSpecAgent
features = [
	ActionFeature,
	PriceFeature,
	VolumeFeature,
	CandlestickPattern
]
predictors = [
	MovingAverageCrossOverAgent,
	ExpMovingAverageCrossOverAgent,
	HodrickPrescottFeature,
	CandlestickFeature,
	PassthroughFeature,
	StochasticOscillatorAgent,
	RetroSpecAgent
	]