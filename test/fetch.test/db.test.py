import sys; 
sys.path.append('../../src/fetch')
sys.path.append('../../src/python')
import unittest
from db import DatabaseGateway, DatabaseException
from core import AppConfig, OsExpert, StringExpert
import os
import uuid
import time
from app import App

class TestCase(unittest.TestCase):
	def setUp(self):
		self.db = DatabaseGateway()
		pass
	def tearDown(self):
		pass
	def test_one_or_more_datasources_exist(self):
		frame = self.db.datasources_frame()
		self.assertFalse(frame.empty)
	def test_datafetch_api_id_by_handler_filepath(self):
		for i in range(1, 3): # ensure some data exists
			some_guid = uuid.uuid4()
			id = self.db.datafetch_api_id_by_handler_filepath(
				'/some/filepath/{}'.format(some_guid), 
				create_if_nonexisting = True
				)
		frame = self.db.datafetch_apis_frame()
		self.assertFalse(frame.empty)
		for i, row in frame.iterrows():
			handler_filepath = row['handler_filepath']
			id = self.db.datafetch_api_id_by_handler_filepath(handler_filepath)			
	def test_datafetch_api_id_error_by_nonexisting_handler_filepath(self):
		with self.assertRaises(DatabaseException):
			id = self.db.datafetch_api_id_by_handler_filepath('/some/nonexisting/filepath')			
	def test_datafetch_api_id_create_by_nonexisting_handler_filepath(self):
		some_guid = uuid.uuid4()
		handler_filepath = '/some/filepath/{}'.format(some_guid)
		insert_id = self.db.datafetch_api_id_by_handler_filepath(handler_filepath, create_if_nonexisting = True)
		id = self.db.datafetch_api_id_by_handler_filepath(handler_filepath)
		self.assertEqual(insert_id, id)
	def test_get_datasource_id_by_name(self):
		id = self.db.datasource_id_by_name('bitcoincharts')
		self.assertEqual(id, 1)
	def test_one_or_more_currencies_exist(self):
		self.assertFalse(
			self.db.currencies_frame().empty
			)
	def test_one_or_more_exchanges_exist_using_frame(self):
		self.assertFalse(
			self.db.exchanges_frame().empty
			)
	def test_one_or_more_exchanges_exist(self):
		self.assertGreater(
			len(self.db.exchanges()), 0
			)
	def test_exchange_id_by_name(self):
		self.assertEqual(
			self.db.exchange_id_by_name('bitstamp'), 1
			)
	def test_get_currency_id_by_code(self):
		self.assertEqual(
			self.db.currency_id_by_code('USD'), 1
			)
	def test_get_crypto_transactions(self):
		self.db.transactions()
	def test_create_datafetch_api_response(self):
		response_text = 'some unique text {}'.format(uuid.uuid4())
		handler_filepath = '/some/filepath/{}'.format(uuid.uuid4())
		datafetch_api_id = self.db.datafetch_api_id_by_handler_filepath(handler_filepath, create_if_nonexisting = True)
		datafetch_api_id = self.db.create_datafetch_api_response({
				'datafetch_api_id': datafetch_api_id,
				'datasource_id': 1,
				'exchange_id': 1,
				'from_currency_id': 1,
				'to_currency_id': 1,
				'response': response_text,
				'response_md5hash': StringExpert.md5hash(response_text)
			})
		self.assertGreater(datafetch_api_id, 0)
	def test_one_or_more_datasources_exist(self):
		l = self.db.datasources()
		self.assertGreater(len(l), 0)
	def test_one_or_more_currencies_exist(self):
		l = self.db.currencies()
		self.assertGreater(len(l), 0)
	def test_create_transaction(self):
		current_time_epoch = int(time.time())
		transaction_id = self.db.create_transaction({
				'datasource_id': 1,
				'exchange_id': 1,
				'amount': 12.45,
				'price': 67.89,
				'from_currency_id': 1,
				'to_currency_id': 1,
				'volume': None,
				'volume_percent': None,
				'source_md5hash': StringExpert.md5hash(str(current_time_epoch)),
				'epoch_time': current_time_epoch
			})
		self.assertGreater(transaction_id, 0)
		print(transaction_id)
		print(self.db.transactions())
if __name__ == '__main__':
	parent_dirpath = OsExpert.path_backstep(__file__, backsteps=2) 
	App.initialize_in_dir(parent_dirpath)
	unittest.main()
    
