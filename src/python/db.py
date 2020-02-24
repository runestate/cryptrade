import pymysql
from core import AppConfig, ObjectExpert
import numpy as np
import pandas as pd
from applogging import Log
import re
import warnings
import os
import collections
from datetime import datetime
import sys

warnings.filterwarnings('error', category=pymysql.Warning)

class DatabaseException(Exception):
    pass
class DuplicateInsertException(DatabaseException):
    pass
class NotFoundException(DatabaseException):
    pass
class Datasource(
	collections.namedtuple('Datasource', [
		'id', 'name', 'epoch_createtime'		
		])
	):
	def __init__(self, *args):
		assert isinstance(self.id, int)
		assert isinstance(self.name, str)
		assert isinstance(self.epoch_createtime, datetime)
class Currency(
	collections.namedtuple('Currency', [
		'id', 'name', 'code', 'is_crypto', 'epoch_createtime'		
		])
	): 
	def __init__(self, *args):
		assert isinstance(self.id, int)
		assert isinstance(self.name, str)
		assert isinstance(self.code, str)
		assert isinstance(self.is_crypto, int)
		assert self.is_crypto == 0 or self.is_crypto == 1		
		assert isinstance(self.epoch_createtime, datetime)
class Exchange(
	collections.namedtuple('Currency', [
		'id', 'name', 'epoch_createtime'		
		])
	): 
	def __init__(self, *args):
		assert isinstance(self.id, int)
		assert isinstance(self.name, str)
		assert isinstance(self.epoch_createtime, datetime)
class DatabaseGateway:
	def __init__(self):
		self.host = AppConfig.setting('DB_HOST')
		self.user = AppConfig.setting('DB_USER')
		self.password = AppConfig.setting('DB_PASSWORD')
		self.db_name = AppConfig.setting('DB_NAME')
	def __dict_to_insert_sql(self, table_name, d):
		keys = list(d.keys())
		values = ['NULL' if v is None else "'" + str(v) + "'" for v in list(d.values())]
		return 'INSERT INTO {} ({}) VALUES ({})'.format(
			table_name, 
			','.join(keys),
			','.join(values)
			)
	def __frame_row(self, frame, col_name, col_value):
		if frame.empty == True:
			raise Exception('Input frame is empty')
		if frame.shape[0] == 0:
			raise Exception('Input frame has zero rows')
		if frame.shape[1] == 0:
			raise Exception('Input frame has zero columns')
		rows = frame.loc[frame[col_name] == col_value]
		rowCount = rows.shape[0]
		if not rowCount == 1:
			raise Exception('Not exactly one row match ({} matched)'.format(rowCount))
		return rows # i.e contains a single row
	def __connection(self):
		return pymysql.connect(
			host=self.host, 
			user=self.user,
			passwd=self.password,
			db=self.db_name
			)
	def transaction_frame(self, min_id=None):
		return self.__query_frame(
			'SELECT * FROM transaction {}'.format(
				'' if min_id is None else 'WHERE id >= {}'.format(min_id)
				)	 
			)
	def transaction_by_timestamp_frame(self, min_timestamp, count, from_currency_ids, to_currency_ids):
		sql = """
			SELECT DISTINCT transaction.* FROM transaction JOIN (
				SELECT epoch_time FROM transaction 
				WHERE epoch_time > {0} 
				AND   from_currency_id IN ({2})
				AND   to_currency_id IN ({3})
				ORDER BY epoch_time
				LIMIT {1}
            ) epoch_times 
			ON transaction.epoch_time IN (epoch_times.epoch_time)
			WHERE from_currency_id IN ({2})
			AND   to_currency_id IN ({3})
			ORDER BY epoch_time
			""".format(
				min_timestamp, 
				count,
				','.join(str(i) for i in from_currency_ids), 
				','.join(str(i) for i in to_currency_ids)
				)
		return self.__query_frame(sql)
	def transaction_count(self, transaction_min_timestamp):
		sql = 'SELECT COUNT(*) FROM transaction WHERE epoch_time >= {}'.format(transaction_min_timestamp)
		return self.__scalar_query(sql)
	def __count_query(self, table_name):
		return self.__scalar_query('SELECT COUNT(*) FROM {}'.format(table_name))
	def __scalar_query(self, sql):
		try:		
			frame = self.__query_frame(sql)
			row_count = frame.shape[0]
			col_count = frame.shape[1]
			assert row_count == 1, 'Not exactly one row ({} returned)'.format(row_count)
			assert col_count == 1, 'Not exactly one column ({} returned)'.format(col_count)
			return frame.iloc[0,0]
		except Exception as e:
			raise Exception('Failed to get scalar from query: ' + sql) from e
	def create_transaction(self, transaction):
		return self.__table_insert_id(
			'transaction', 
			['datasource_id', 'exchange_id', 'amount', 'price', 'from_currency_id', 'to_currency_id', 'source_md5hash', 'epoch_time', 'volume', 'volume_percent'], 
			transaction)
	def create_datafetch_api_response(self, datafetch_api_response):
		return self.__table_insert_id(
			'datafetch_api_response',
			['datafetch_api_id', 'datasource_id', 'exchange_id', 'from_currency_id', 'to_currency_id', 'response', 'response_md5hash', 'response_filename', 'epoch_receive_time'],
			datafetch_api_response
			)
	def datafetch_api_view_frame(self):
		return self.__select_all('datafetch_api_view')
	def datafetch_apis_frame(self):
		return self.__select_all('datafetch_api')
	def create_datafetch_api(self, datafetch_api):
		return self.__table_insert_id(
			'datafetch_api',
			['handler_filepath', 'result_endpoint', 'result_frequency_seconds'],
			datafetch_api
			)
	def datafetch_api_id_by_handler_filepath(self, handler_filepath, datafetch_api_ids = None, create_if_nonexisting = False):
		table_name = 'datafetch_api'
		col_name = 'handler_filepath'
		scalar_col_name = 'id'
		if create_if_nonexisting == True:
			result =  self.__scalar_by_unique_col_value(
				table_name, col_name, handler_filepath, scalar_col_name, 
				frame = datafetch_api_ids,
				nonexisting_is_error = False
				)
			if result is not None:
				return result
			handler_filename = os.path.basename(handler_filepath)
			result_endpoint_prefix = AppConfig.setting('RESULT_ENDPOINT_PREFIX')
			result_endpoint = '{}{}'.format(result_endpoint_prefix, handler_filename)
			new_datafetch_api_id = self.create_datafetch_api({
					'handler_filepath': handler_filepath,
					'result_endpoint': result_endpoint,
					'result_frequency_seconds': 30
				})
			Log.d('created datafetch api id {} for handler filepath "{}"', new_datafetch_api_id, handler_filepath)
		return self.__scalar_by_unique_col_value(
			table_name, col_name, handler_filepath, scalar_col_name, 
			frame = datafetch_api_ids
			)
	def unparsed_datafetch_api_responses_frame(self, min_id = 0, limit=100):
		sql = """
			SELECT {0}.* FROM {0}
			LEFT OUTER JOIN {1} ON 
							{1}.source_md5hash = {0}.response_md5hash
			WHERE 
				{1}.source_md5hash IS NULL 
			AND 
				{0}.id >= {2}
            ORDER BY {0}.id
            LIMIT {3}
			""".format('datafetch_api_response', 'transaction', min_id, limit)
		Log.d('executing:\n{}', sql) 
		sys.stdout.flush()
		return self.__query_frame(sql)
	def __scalar_by_unique_col_value(self, table_name, col_name, col_value, scalar_col_name, frame = None, nonexisting_is_error = True):
		try:
			if frame is None:
				frame = self.__select_all(table_name)
			row = self.__frame_row(frame, col_name, col_value)
			return row[scalar_col_name].values[0]
		except Exception as e:
			if nonexisting_is_error != True:
				return None
			raise DatabaseException('Failed to get entity {} column "{}" scalar by column "{}" with unique value "{}"'.format(
				table_name, scalar_col_name, col_name, col_value
				)) from e
	def __table_insert_entity(self, table_name, expected_keys, insert_dict):
		try:
			id = self.__table_insert_id(table_name, expected_keys, insert_dict)
			frame = self.__query_frame('SELECT * FROM {} WHERE ID = {}'.format(table_name, id))
			row_count = frame.shape[0]
			assert row_count == 1, 'Not exactly one row ({} returned)'.format(row_count)
			return frame.iloc[0]
		except Exception as e:
			raise Exception('Failed to insert and get inserted entity by id') from e
	def __table_insert_id(self, table_name, expected_keys, insert_dict):
		db = None
		try: 
			db = self.__connection()
			ObjectExpert.ensure_dict_keys(
				insert_dict,
				expected_keys
				)
			sql = self.__dict_to_insert_sql(table_name, insert_dict)
			with db.cursor() as cur:
				cur.execute(sql)
				db.commit()
				return cur.lastrowid
		except pymysql.err.IntegrityError as e:
			if re.match(r".+Duplicate entry '.+' for key .+", str(e)):
				raise DuplicateInsertException() from e
			else:
				raise e
		except Exception as e:
			raise DatabaseException('Failed to create entity "{}"'.format(table_name)) from e
		finally:
			if db is not None:
				db.close()
	def transactions(self):
		return self.__select_all('transaction')
	def datasources_frame(self):
		return self.__select_all('datasource')
	def datasources(self):
		return list(self.datasources_iterate())
	def datasources_iterate(self):
		return self.__select_all_as_named_tuples('datasource', Datasource)
	def __select_all_as_named_tuples(self, table_name, factory):
		frame = self.__select_all(table_name)
		for row in frame.itertuples():
			yield factory(*row[1:])		
	def datasource_id_by_name(self, name, datasources = None):
		if datasources is None:
			datasources = self.datasources_frame()
		try:
			row = self.__frame_row(datasources, 'name', name)
			return row['id'].values[0]
		except Exception as e:
			raise DatabaseException('Failed to get datasource id by name "{}"'.format(name)) from e
	def currencies_frame(self):
		return self.__select_all('currency')
	def currencies_iterate(self):
		return self.__select_all_as_named_tuples('currency', Currency)
	def currencies(self):
		return list(self.currencies_iterate())
	def currency_id_by_code(self, code, currencies = None):
		if currencies is not None:
			raise Exception('Cached frame not implemented')
		return self.__scalar_query('SELECT id FROM currency where code = "{}"'.format(code))
	def exchanges(self):
		return list(self.exchanges_iterate())
	def exchanges_iterate(self):
		return self.__select_all_as_named_tuples('exchange', Exchange)
	def exchanges_frame(self):
		return self.__select_all('exchange')
	def exchange_id_by_name(self, name, exchanges = None):
		if exchanges is None:
			exchanges = self.exchanges_frame()
		try:
			row = self.__frame_row(exchanges, 'name', name)
			return row['id'].values[0]
		except Exception as e:
			raise DatabaseException('Failed to get exchange provider id by name "{}"'.format(name)) from e
	def __select_all(self, tableName):
		return self.__query_frame('SELECT * FROM ' + tableName)
	def __query_frame(self, query):
		db = self.__connection()
		with db.cursor() as cursor:
			cursor.execute(query)
			rows = cursor.fetchall()
			colnames = [i[0] for i in cursor.description]
			db.close()
			frame = pd.DataFrame(
				np.array(rows) if len(rows) > 0 else None, 
				columns=colnames
				)
			return frame
