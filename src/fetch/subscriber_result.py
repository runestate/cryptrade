import collections

class SubscriberResult(
	collections.namedtuple('SubscriberResult', [
		'reponse_length',
		'response_text',
		'response_md5hash',
		'datasource_id',
		'exchange_id',
		'from_currency_id',
		'to_currency_id'
		])
	): pass
