from applogging import Log
import json

class BitcoinAverageParser: 
	def __init__(self):
		self.datasource_name = 'bitcoinaverage'
	def parse(self, result):
		response_text = result['response']
		if not response_text:
			raise ValueError('could not parse empty response text')
		Log.t('parsing text: {}', response_text)
		response_dict = json.loads(response_text)
		type_key = 'type'
		if type_key in response_dict:
			type_value = response_dict[type_key]
			if not type_value == 'status':
				raise Exception('Unexpected type value "{}"'.format(type_value))
			Log.t('ignoring status message')
			return None
		event_key = 'event' # assume response can now only be of the 'event' type
		event_value = response_dict[event_key]
		if event_value != 'message':
			raise Exception('Cannot handle event value "{}"'.format(event_value))
		data_value = response_dict['data']
		data_success_value = data_value['success']
		if data_success_value != True:
			raise Exception('Unexpected success value "{}"'.format(data_success_value))
		display_time_epoch = data_value['timestamp']
		last_price = data_value['last']
		volume = data_value['volume']
		volume_percent = data_value['volume_percent']
		transaction = {
				'datasource_id': result['datasource_id'],
				'exchange_id': result['exchange_id'],
				'amount': 0, # transaction with zero amount indicates the current market value
				'price': last_price,
				'from_currency_id': result['from_currency_id'],
				'to_currency_id': result['to_currency_id'],
				'volume': volume,
				'volume_percent': volume_percent,
				'source_md5hash': result['response_md5hash'],
				'epoch_time': display_time_epoch
			}
		return transaction
		
