import sys
sys.path.append('..')
from applogging import Log
import requests
import gzip
import csv
import time
from db import DatabaseGateway, DuplicateInsertException
import os
from core import AppConfig, OsExpert
import datetime

AppConfig.initialize_in_file_dir(
	OsExpert.path_backstep(__file__)
	)     
def downloadFile(url, filepath):
	if url is None:
		raise ValueError('parameter "value" not specified')
	if filepath is None:
		raise ValueError('parameter "filepath" not specified')
	Log.d('Downloading to path {}: {}'.format(filepath, url))
	r = requests.get(url, stream=True) # NOTE the stream=True parameter
	with open(filepath, 'wb') as f:
		for chunk in r.iter_content(chunk_size=1024): 
			if chunk: # filter out keep-alive new chunks
				f.write(chunk)
    
jobs = [
	{
		'datasource_name': 'bitcoincharts',
		'provider_name': 'bitstamp',
		'currency_code': 'EUR',
		'url': 'http://api.bitcoincharts.com/v1/csv/bitstampEUR.csv.gz'
	},
	{
		'datasource_name': 'bitcoincharts',
		'provider_name': 'bitstamp',
		'currency_code': 'USD',
		'url': 'http://api.bitcoincharts.com/v1/csv/bitstampUSD.csv.gz'
	}
	{
		'datasource_name': 'bitcoincharts',
		'provider_name': 'coinbase',
		'currency_code': 'EUR',
		'url': 'http://api.bitcoincharts.com/v1/csv/coinbaseEUR.csv.gz'
	}
	]
def retrieve(db, url, datasource_id, exchange_id, currency_id):
	temp_dirpath=AppConfig.setting('TEMP_DIRPATH')
	filepath = os.path.join(temp_dirpath, url.split('/')[-1])
	downloadFile(url, filepath)
	duplicateCount = 0
	insertCount = 0
	with gzip.open(filepath, 'rt') as f:
		Log.d('Processing csv file..')
		spamreader = csv.reader(f, delimiter=',', quotechar='|')
		for row in spamreader:
			timeStr = row[0]
			epochTime = int(timeStr)
			priceStr = row[1]
			price = float(priceStr)
			amountStr = row[2]
			amount = float(amountStr)
			transaction = {
				'datasource_id': datasource_id,
				'exchange_id': exchange_id,
				'amount': amount,
				'price': price,
				'currency_id': currency_id,
				'epoch_time': epochTime,
			}
			try:
				db.create_transaction(transaction)
				insertCount += 1
			except DuplicateInsertException as e:
				duplicateCount += 1
	os.remove(filepath)
	Log.i('Done processing, insert count: {}, duplicate count: {}', insertCount, duplicateCount)
db = DatabaseGateway()
currencies = db.currencies_frame()
datasources = db.datasources_frame()
for i, job in enumerate(jobs):
	url = job['url']
	Log.i('Processing job {}/{}'.format(i + 1, len(jobs)))
	start_time = datetime.datetime.now()
	datasource_id = db.datasource_id_by_name(job['datasource_name'])
	exchange_id = db.exchange_id_by_name(job['provider_name'])
	currency_code = db.currency_id_by_code(job['currency_code'])
	retrieve(
		db, 
		url,
		datasource_id,
		exchange_id,
		currency_code
		)	
	time_spent = datetime.datetime.now() - start_time
	Log.i('Done with job, time spent: {}', time_spent)
