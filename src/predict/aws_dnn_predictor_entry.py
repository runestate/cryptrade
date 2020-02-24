import os
import tensorflow as tf
from tensorflow.python.platform import gfile
import numpy as np
import csv
import logging

INPUT_TENSOR_NAME = 'inputs'
test_filename  = 'sagemaker_test.csv'
train_filename = 'sagemaker_train.csv'
meta_filename  = 'sagemaker.json'
training_dir_abs = '/opt/ml/input/data/training'

def _meta_dict():
	meta_filepath = os.path.join(training_dir_abs, meta_filename)
	with open(meta_filepath, 'r') as f:
		return eval(f.read())
def _load_csv_with_header(filename,
						 target_dtype,
						 features_dtype,
						 target_column=-1):
	with gfile.Open(filename) as csv_file:
		row_reader = csv.reader(csv_file)
		header = next(row_reader)
		row_count = sum(1 for row in row_reader)
	with gfile.Open(filename) as csv_file:
		data_file = csv.reader(csv_file)
		header = next(data_file)
		n_samples = row_count
		n_features = len(header) -1
		data = np.zeros((n_samples, n_features), dtype=features_dtype)
		target = np.zeros((n_samples,), dtype=target_dtype)
		for i, row in enumerate(data_file):
			target_val = row.pop(target_column)
			parsed_row = row
			try:
				target[i] = np.asarray(float(target_val), dtype=target_dtype) #TODO: remove -4
				data[i] = np.asarray(parsed_row, dtype=features_dtype)
			except Exception as e:
			    print('failed to process target val {} and row: {}'.format(target_val, parsed_row))
			    raise e
		return tf.contrib.learn.datasets.base.Dataset(data=data, target=target)
if __name__ == '__main__':
    print('loading test..')
    f = _load_csv_with_header(test_filename, target_dtype=np.int, features_dtype=np.float32, target_column=-1)
    print('loading train..')
    f = _load_csv_with_header(train_filename, target_dtype=np.int, features_dtype=np.float32, target_column=-1)
    print('===== main done')
    pass
def estimator_fn(run_config, params):
	logger = logging.getLogger('default')
	logger.log(logging.INFO, '=== estimator_fn ===')
	logger.log(logging.INFO, 'estimator_fn, file: {}'.format(__file__))
	logger.log(logging.INFO, 'estimator_fn, run_config: {}'.format(run_config))
	logger.log(logging.INFO, 'estimator_fn, params: {}'.format(params))
	meta = _meta_dict()
	logger.log(logging.INFO, 'meta dict: {}'.format(meta))
	feature_count = meta['feature_count']
	feature_columns = [tf.feature_column.numeric_column(INPUT_TENSOR_NAME, shape=[feature_count])]
	return tf.estimator.DNNClassifier(feature_columns=feature_columns,
									  hidden_units=[10, 20, 10],
									  n_classes=3,
									  config=run_config)
"""
	During training, a train_input_fn() ingests data and prepares it for use by the model. 
	At the end of training, similarly, a serving_input_fn() is called to create the model that 
	will be exported for Tensorflow Serving.
	Use this function to do the following:
		- Add placeholders to the graph that the serving system will feed with inference requests.
		- Add any additional operations needed to convert data from the input format into the 
		 feature Tensors expected by the model.
	The function returns a tf.estimator.export.ServingInputReceiver object, which packages the placeholders
	  and the resulting feature Tensors together.
	Typically, inference requests arrive in the form of serialized tf.Examples, so the 
	  serving_input_receiver_fn() creates a single string placeholder to receive them. The serving_input_receiver_fn() 
	  is then also responsible for parsing the tf.Examples by adding a tf.parse_example operation to the graph.
	For more information on how to create a serving_input_fn, see 
	  https://github.com/tensorflow/tensorflow/blob/18003982ff9c809ab8e9b76dd4c9b9ebc795f4b8/tensorflow/docs_src/programmers_guide/saved_model.md#preparing-serving-inputs.
	
	Args:   
	 hyperparameters: The hyperparameters passed to your TensorFlow Amazon SageMaker estimator that 
		   deployed your TensorFlow inference script. You can use this to pass hyperparameters 
		   to your inference script.
	"""
def serving_input_fn(params):
	logger = logging.getLogger('default')
	logger.log(logging.INFO, '=== serving_input_fn ===')
	logger.log(logging.INFO, 'serving_input_fn, file: {}'.format(__file__))
	logger.log(logging.INFO, 'serving_input_fn, params: {}'.format(params))
	meta = _meta_dict()
	feature_count = meta['feature_count']
	feature_spec = {
			INPUT_TENSOR_NAME: tf.FixedLenFeature(dtype=tf.float32, shape=[feature_count])
		}
	return tf.estimator.export.build_parsing_serving_input_receiver_fn(feature_spec)()
"""
Implement code to do the following:
1. Read the **training** dataset files located in training_dir
2. Preprocess the dataset
3. Return 1) a mapping of feature columns to Tensors with
the corresponding feature data, and 2) a Tensor containing labels
For more information on how to create a input_fn, see https://www.tensorflow.org/get_started/input_fn.
Args:
	training_dir:    Directory where thecated inside the container.
	hyperparameters: The hyperparameters passed to your Amazon SageMaker TrainingJob that 
	   runs your TensorFlow training script. You can use this to pass hyperparameters 
	   to your training script.
Returns: (data, labels) tuple
"""
def train_input_fn(training_dir, params):
	logger = logging.getLogger('default')
	logger.log(logging.INFO, '=== train_input_fn ===')
	logger.log(logging.INFO, 'train_input_fn, file: {}'.format(__file__))
	logger.log(logging.INFO, 'train_input_fn, training_dir: {}'.format(training_dir))
	logger.log(logging.INFO, 'train_input_fn, params: {}'.format(params))
	"""Returns input function that would feed the model during training"""
	return _generate_input_fn(training_dir, train_filename)
"""Returns input function that would feed the model during evaluation"""
"""
Implement code to do the following:
1. Read the **evaluation** dataset files located in training_dir
2. Preprocess the dataset
3. Return 1) a mapping of feature columns to Tensors with
the corresponding feature data, and 2) a Tensor containing labels
For more information on how to create a input_fn, see https://www.tensorflow.org/get_started/input_fn.
Args:
 training_dir: The directory where the dataset is located inside the container.
 hyperparameters: The hyperparameters passed to your Amazon SageMaker TrainingJob that 
	   runs your TensorFlow training script. You can use this to pass hyperparameters 
	   to your training script.
Returns: (data, labels) tuple
"""
def eval_input_fn(training_dir, params):
	logger = logging.getLogger('default')
	logger.log(logging.INFO, '=== eval_input_fn ===')
	logger.log(logging.INFO, 'eval_input_fn, file: {}'.format(__file__))
	logger.log(logging.INFO, 'eval_input_fn, training_dir: {}'.format(training_dir))
	logger.log(logging.INFO, 'eval_input_fn, params: {}'.format(params))
	return _generate_input_fn(training_dir, test_filename)
def _generate_input_fn(training_dir, training_filename):
	training_set = _load_csv_with_header(
		filename=os.path.join(training_dir, training_filename),
		target_dtype=np.int,
		features_dtype=np.float32)
	return tf.estimator.inputs.numpy_input_fn(
		x={INPUT_TENSOR_NAME: np.array(training_set.data)},
		y=np.array(training_set.target),
		num_epochs=None,
		shuffle=True)()
