from numpy import nan, float64
from feature_value import FeatureValue
PREDICT_ACTION = 'predict_action'
FEATURE_HODPRES_VALUE = 'feature_hodpres_value'

class EnsemblePredictor:
	def process(self, r_index, df):
		if PREDICT_ACTION not in df:
			df[PREDICT_ACTION] = nan
		if len(df) < 2:
			return
		r1 = df.iloc[r_index]
		r2 = df.iloc[r_index - 1]			
		previous_hodpress_value = r2[FEATURE_HODPRES_VALUE]
		current_hodpress_value = r1[FEATURE_HODPRES_VALUE]
		action = float64(FeatureValue.BUY) if (
			previous_hodpress_value == FeatureValue.DOWNTREND and 
			current_hodpress_value == FeatureValue.UPTREND
				) else float64(FeatureValue.SELL) if (
					previous_hodpress_value == FeatureValue.UPTREND and 
					current_hodpress_value == FeatureValue.DOWNTREND
					) else nan
