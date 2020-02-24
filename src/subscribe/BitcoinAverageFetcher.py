import json
import time
import configparser
import io
import os
import hashlib
import requests
import hmac
import websocket
import simplejson as json
from applogging import Log
from core import AppConfig, OsExpert, StringExpert, Market 
from enum import Enum     # for enum34, or the stdlib version
import aiohttp
import traceback
from datetime import datetime
from pathlib import Path
import urllib
from .bitcoinaverage_parser import BitcoinAverageParser

class BitcoinAverageFetcher(BitcoinAverageParser):
	def __init__(self, handler_file, from_currency_code, to_currency_code, market):
		super().__init__()
		try:
			self.from_currency_code = from_currency_code
			self.to_currency_code = to_currency_code
			self.market = market
			self.exchange_prefix = 'multiple_'
			path = Path(handler_file)
			self.handler_filename = path.stem
			self.handler_filepath = os.path.abspath(handler_file)
		except Exception as e: 
			raise Exception('Failed to contruct') from e
	def market_name(self):
		return self.market.name.lower()
	async def __socket_subscribe(self):
		try:
			publicKey = AppConfig.setting('BITCOINAVERAGE_PUBLIC_KEY')
			secretKey = AppConfig.setting('BITCOINAVERAGE_SECRET_KEY')
			timestamp = int(time.time())
			payload = '{}.{}'.format(timestamp, publicKey)
			hex_hash = hmac.new(secretKey.encode(), msg=payload.encode(), digestmod=hashlib.sha256).hexdigest()
			signature = '{}.{}'.format(payload, hex_hash)
			ticket_url = 'https://apiv2.bitcoinaverage.com/websocket/get_ticket'
			ticket_header = {'X-signature': signature}
			async with aiohttp.ClientSession() as session:
				async with session.get(ticket_url, headers=ticket_header) as resp:
					response_text = await resp.text()
					Log.d('received ticket response: {}', response_text)
					if response_text == 'Client limit reached for api key apikey':
						raise Exception(response_text)
					response_json = json.loads(response_text)
					ticket = response_json['ticket']
			Log.d('ticket received: {}', ticket)
			url = 'wss://apiv2.bitcoinaverage.com/websocket/ticker?public_key={}&ticket={}'.format(publicKey, ticket)			
			subscribe_message = json.dumps({
					'event': 'message',
					'data': {
						'operation': 'subscribe',
						'options': {
							'currency': '{}{}'.format(self.from_currency_code, self.to_currency_code),
							'market': self.market_name()
						}
					}
				})
			Log.d('sending subscribe message: {}', subscribe_message)
			session = aiohttp.ClientSession()
			async with session.ws_connect(url) as ws:
				await ws.send_str(subscribe_message)
				async for msg in ws:
					if msg.type == aiohttp.WSMsgType.CLOSED:
						raise Exception('Socket presumed invalidated as received message was of aiohttp type "closed"')
					if msg.type == aiohttp.WSMsgType.ERROR:
						raise Exception('Socket presumed invalidated as received message was of aiohttp type "error"')
					result = msg.data
					yield result
		except Exception as e:
			raise Exception('Failed to subscribe via socket') from e
	async def subscribe(self):	
		try:
			async for response_text in self.__socket_subscribe():
				Log.t('received text: {}', response_text)
				yield response_text
		except Exception as e:
			error_msg = 'Failed to subscribe for handler filepath {}'.format(self.handler_filepath)
			raise Exception(error_msg) from e
	def __dict_get(self, key, d):
		if not key in d:
			raise Exception('Key "{}" not present in dictionary'.format(key))
		return d[key]
