{
	"datasource_name": ["bitcoinaverage"],
	"gap_resolver": None,
	"exchange_name": ["multiple_global"],
	"from_currency_code": ["ETH"],
	"to_currency_code": ["USD"],
	"agent_config": {
		PassthroughFeature.__name__: None,
		CandlestickFeature.__name__: None,
		HodrickPrescottFeature.__name__: [
			{
				"frame_history_minutes": [0],
				"lamb": [10_000]
			}
			],
		MovingAverageCrossOverAgent.__name__: [
			{
				"slow_avg_seconds": [3600 * 24 * day],
				"fast_avg_seconds": [3600 * 24 * day * 0.25],
				"tag": ["day{}".format(day)]
			}
			for day in [1, 10]
			],
		ExpMovingAverageCrossOverAgent.__name__: [
			{
				"slow_avg_seconds": [3600 * 24],
				"fast_avg_seconds": [3600] ,
				"slow_alpha": [0.02*alpha_factor],
				"fast_alpha": [0.05*alpha_factor], # i.e. more weight to newer points
				"tag": ["alp{}".format(alpha_factor)]
			}
			for alpha_factor in [0.5, 1]
			],
		StochasticOscillatorAgent.__name__: [
			{
				"period_seconds": [3600 * 24*day],
				"tag": ["day{}".format(day)]
			}
			for day in [1, 10]
			],
		VolumeAgent.__name__: [
			{
				"slow_avg_seconds": [3600 * 24 * 3 * day],
				"fast_avg_seconds": [3600 * 24 * day],
				"tag": ["day{}".format(day)]
			} 
			for day in [1, 10] 
			],
		RetroSpecAgent.__name__: None
	}
}
