from numpy import nan, float64
from pathlib import Path    
from applogging import Log
from threading import Thread
import boto3
from multiprocessing import Event
import sagemaker
from sklearn.model_selection import train_test_split
import pandas as pd
import numpy as np
from sagemaker.tensorflow import TensorFlow, TensorFlowPredictor
from sklearn.metrics import accuracy_score
from pathlib import Path
import os
import json
from core import AppConfig
from datetime import  datetime		
from sagemaker import get_execution_role
import pickle, gzip, numpy, urllib.request, json
from functools import reduce
from predict import FeatureExpert
from predictor_base import PredictorBase

class AwsPredictor(PredictorBase): # TODO: run as process?
	name = 'awsdnn'
	prefix = 'prediction_awsdnn_next_trend_feature'
	def __init__(self, csv_filepath, min_row_count, is_train_async, min_predict_generator_size):
		super().__init__(predict_col='feature_rtrspc()_next_trend_pricefeature')
		csv_file = Path(csv_filepath)
		assert csv_file.is_dir(), csv_filepath
		self.csv_filepath = csv_filepath
		self.write_count = 0
		self.predict_count = 0
		self.train_filepath = os.path.join(csv_filepath, 'sagemaker_train.csv')
		self.test_filepath  = os.path.join(csv_filepath, 'sagemaker_test.csv')
		self.meta_filepath  = os.path.join(csv_filepath, 'sagemaker.json')
		if Path(self.train_filepath).exists():
			os.remove(self.train_filepath)
		if Path(self.test_filepath).exists():
			os.remove(self.test_filepath)
		if Path(self.meta_filepath).exists():
			os.remove(self.meta_filepath)
		self.predictor = None
		self.is_train_async = is_train_async
		self.csv_changed_event = Event() if is_train_async else None
		self.min_predict_generator_size = min_predict_generator_size 
		if is_train_async is True:
			Log.w('oops is_train_async, we dont allow yet')
			exit()
			Thread(target=self.csv_write_event_handler).start()
	def process(self, epoch, df):
		if df.empty:
			Log.d('skipping processing of empty dataset')
			return
		r_index = df.index.get_loc(epoch)
		if self.predictor is not None:	
			row_frame = df[r_index:r_index + 1]
			return self.__predict(row_frame)
		not_enough_predictor_data = r_index +1 < self.min_predict_generator_size 
		if not_enough_predictor_data:
			return
		Log.d('initiating predictor contruction at index {}, frame length {}', r_index, len(df))
		predictor = self.predictor_from_config_maybe()
		if predictor is not None:
			self.predictor = predictor
			Log.i('existing predictor endpoint loaded: {}', predictor.endpoint)
			return
		train_df = df[:r_index +1]
		Log.i('at index {}, detected data of adequate length {} writing csv', r_index, len(train_df), self.csv_filepath)
		self.write_csv(train_df)
		return None
	def predictor_from_config_maybe(self):
		endpoint = AppConfig.setting('AWS_DNN_PREDICTOR_ENDPOINT')
		return TensorFlowPredictor(endpoint) if endpoint not in (None, '') else None
	def __enter__(self):
		return self
	def __exit__(self, type, value, traceback):
		self.close()
	def close(self):
		Log.d('closing')
		if self.predictor is not None:
			endpoint = self.predictor.endpoint
	def __predict(self, df):
		max_prediction_count = 100
		if self.predict_count >= max_prediction_count:
			Log.w('too many predictions {} reached, exiting', self.predict_count)
			exit()
		assert len(df) == 1
		X_all, y_all = self.frame_to_ml_inputs(df)
		predict_row = X_all.iloc[0]
		Log.d('predicting based on {} values:\n{}', len(predict_row.values), predict_row.squeeze().sort_index())
		prediction_response = self.predictor.predict(predict_row.values)
		prediction = self.sagemaker_response_highest_score_label(prediction_response)
		self.predict_count += 1
		return prediction 
	def sagemaker_response_highest_score_label(self, prediction_response):
		Log.d('parsing response: {}', prediction_response)
		classifications = prediction_response['result']['classifications']
		assert len(classifications) == 1
		classification = classifications[0]
		classes = classification['classes']
		Log.d('parsing classes: {}', classes)
		label_scores = { c['score']:c['label'] for c in classes if 'score' in c }
		assert len(label_scores) > 0
		scores = sorted(label_scores.keys(), reverse=True)
		assert all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
		win_score = scores[0]
		win_label = int(label_scores[win_score])
		Log.d('winner is \'{}\' in score: {}', win_label, label_scores)
		return win_label
	def write_csv(self, df):
		if self.write_count > 0:
			Log.w('ignoring csv write because it has already been performed')
			return
		X_all, y_all = self.frame_to_ml_inputs(df, do_filter=True)
		assert len(X_all) == len(y_all)
		if X_all.empty:
			Log.w('no rows to write!')
			return
		y_null_count = y_all.isnull().sum()
		assert y_null_count == 0, 'null count: {}'.format(y_null_count)
		X_train, X_test, y_train, y_test = train_test_split(X_all, y_all, test_size=0.2, random_state=123)
		Log.d('X train shape: {}, X test shape: {}', X_train.shape, X_test.shape)
		train = pd.concat([X_train, y_train], axis=1)
		test = pd.concat([X_test, y_test], axis=1)
		is_first_write = (self.write_count == 0)
		for frame, filepath in ((train, self.train_filepath), (test, self.test_filepath)):
			Log.d('writing csv: {}', filepath)
			frame.to_csv(filepath, sep=',', na_rep='', index=False, header=is_first_write, decimal='.', mode='+a')#, index=False)
		with open(self.meta_filepath, 'w') as f:
			f.write(json.dumps(
				{
					'train_filename': Path(self.train_filepath).name,
					'test_filename': Path(self.test_filepath).name,
					'train_observation_count': len(X_train),
					'test_observation_count': len(X_test),
					'feature_count': X_all.shape[1]
				},
				indent=4#, sort_keys=True
				))
		self.write_count += 1
		Log.i('done writing csv file, write count is now: {}', self.write_count)
		if self.is_train_async is True:
			Log.d('propagating notification that csv has been written')
			self.csv_changed_event.set()
		else:
			self.create_predictor_from_csv()
	def csv_write_event_handler(self):
		while self.csv_changed_event.wait():
			self.create_predictor_from_csv()
			self.csv_changed_event.clear()
	def create_predictor_from_csv(self):
			Log.i('initiating sagemaker model creation')
			role = AppConfig.setting('AWS_PREDICTOR_ROLE')
			bucket='cryptrade-sagemaker'
			custom_code_upload_location = 's3://{}/customcode/tensorflow_iris'.format(bucket)
			model_artifacts_location = 's3://{}/artifacts'.format(bucket)
			Log.d('training data will be uploaded to: {}', custom_code_upload_location)
			Log.d('training artifacts will be uploaded to: {}', model_artifacts_location)
			sess = sagemaker.Session()
			def upload_to_s3(channel, filepath, skip_if_name_and_size_matches=False):
				file = Path(filepath)
				"""From SM examples. Like here: https://github.com/awslabs/amazon-sagemaker-examples/blob/master/introduction_to_amazon_algorithms/imageclassification_caltech/Image-classification-transfer-learning.ipynb"""
				s3 = boto3.resource('s3')
				key = channel + '/' + file.name
				bucket_ref = s3.Bucket(bucket)
				objs = list(bucket_ref.objects.filter(Prefix=key))
				is_file_already_existing = len(objs) > 0 and objs[0].key == key
				if is_file_already_existing is True:
					if skip_if_name_and_size_matches is True:
						s3_client = boto3.client('s3')
						response = s3_client.head_object(Bucket=bucket, Key=key)
						local_size = file.stat().st_size
						remote_size = response['ContentLength']
						if remote_size == local_size:
							Log.w('skipping upload as s3 key of same size ({:.2f}kb) already exists: {}', local_size/1000, key)
							return
					Log.w('overwriting existing s3 key: {}', key)
				with open(filepath, "rb") as data:
					s3.Bucket(bucket).put_object(Key=key, Body=data)
			s3_data_folder = 'data'
			upload_to_s3(s3_data_folder, self.train_filepath, True)
			upload_to_s3(s3_data_folder, self.test_filepath, True)
			upload_to_s3(s3_data_folder, self.meta_filepath)
			estimator = TensorFlow(
				entry_point='aws_dnn_predictor_entry.py',
				role=role,
				output_path=model_artifacts_location,
				code_location=custom_code_upload_location,
				train_instance_count=1,
				train_instance_type='ml.c5.xlarge',
				training_steps=1000,
				evaluation_steps=100
				)
			train_data_location = 's3://{}/{}'.format(bucket, s3_data_folder)
			Log.i('fitting train data: {}', train_data_location)
			estimator.fit(train_data_location)
			Log.i('deploying model')
			deploy_start = datetime.now()
			predictor = estimator.deploy(initial_instance_count=1,
			                                       instance_type='ml.t2.medium'
			                                       )
			deploy_end = datetime.now()
			Log.i('deployed predictor in {}s, endpoint is:\n{}', deploy_end - deploy_start, predictor.endpoint)
			
			self.predictor = predictor
