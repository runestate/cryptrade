from applogging import Log
from generator import features
import re
from enum import IntEnum
import numpy as np

feature_postfix_map = {
	feature : re.compile('.+_{}$'.format(feature.__name__), re.I)
	for feature in features
	}
class PredictorBase:
	def __init__(self, predict_col):
		self.predict_col = predict_col
	def frame_to_ml_inputs(self, df, do_filter=False, one_hot=True, max_train_size=None):
		assert self.predict_col in df, 'prediction column "{}"  does not exist in columns {}'.format(self.predict_col, df.columns.values)
		predict_col = next(c for c in df.columns.values if c == self.predict_col)
		active_columns = [c for c in df.columns.values if c.endswith('_active')]
		if do_filter is True: #TODO: are empty feature rows filtered out??
			Log.d('filtering out rows with all feature values empty or predictor column empty, if needed')
			df_no_all_empty_feature_values = df.loc[(df[active_columns] == 1).all(axis=1)]
			dropped = df[~df.index.isin(df_no_all_empty_feature_values.index)]
			if len(dropped) > 0:
				Log.w('all-cols-empty drop row count: {}', len(dropped))		
			df_no_empty_predict = df_no_all_empty_feature_values.dropna(subset=[predict_col]) # no point in using empty rows
			dropped = df_no_all_empty_feature_values[~df_no_all_empty_feature_values.index.isin(df_no_empty_predict.index)]
			if len(dropped) > 0:
				Log.w('empty-predict-col drop row count: {}', len(dropped))
			df_filtered = df_no_empty_predict
			keep_ratio =  len(df_filtered) / len(df)
			Log.d('frame row ratio after filtering: {}/{} = {:.2f}', len(df_filtered), len(df), keep_ratio)
			assert keep_ratio < 1
		else:
			df_filtered = df
		if max_train_size is not None:
			count_before = len(df_filtered)
			df_filtered = df_filtered.head(max_train_size)
			drop_count = count_before - len(df_filtered)
			Log.d('row count after train max size trim: {} - {} = {}', count_before, drop_count, len(df_filtered))
		float_feature_cols = set(
			c for c in df.columns.values  	 
			if not c.endswith(predict_col) 
			and c.endswith('_feature')
			)
		category_feature_cols = set()
		for feature, postfix_pattern in feature_postfix_map.items():
			assert issubclass(feature, IntEnum), 'feature {} is not an int enum'.format(feature)
			cols = [ c for c in df.columns.values 
					if not c.endswith(predict_col)
					and postfix_pattern.match(c) ]
			enum_values = [int(k) for k in feature]	
			if one_hot is not True:
				category_feature_cols.update(cols)
			else:	
				kwargs = {}
				for col in cols:
					for enum_value in enum_values:
						enum_name = feature(enum_value).name
						enum_value_col = '{}_{}'.format(col, enum_name.lower())
						kwargs[enum_value_col] = (df_filtered[col] == enum_value).astype(np.float64)
						category_feature_cols.add(enum_value_col)
				df_filtered = df_filtered.assign(**kwargs)
		feature_cols = list(float_feature_cols | category_feature_cols)
		assert len(feature_cols) > 0
		y_all = df_filtered[predict_col]
		assert not y_all.isnull().values.any(), 'one or more values in the predict series were not specified'
		X_all = df_filtered[feature_cols]
		X_all = X_all.fillna(0)
		assert not X_all.isnull().values.any(), 'one or more values in the input frame were not specified, although they should\' been na-filled with zeros'
		return X_all, y_all
