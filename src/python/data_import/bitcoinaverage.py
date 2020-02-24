import sys
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
from core import AppConfig, OsExpert
from db import DatabaseGateway

sys.path.append('..')
AppConfig.initialize_in_file_dir(
	OsExpert.path_backstep(__file__)
	)     
file_path = os.path.realpath(__file__)
print(file_path)
db = DatabaseGateway()
datafetch_api_id = db.datafetch_api_id_by_handler_filepath(file_path)
print(datafetch_api_id)
exit()
def prettyJson(jsonData):
	return json.dumps(jsonData, indent=4, sort_keys=True)
publicKey = AppConfig.setting("BITCOINAVERAGE_PUBLIC_KEY")
secretKey = AppConfig.setting("BITCOINAVERAGE_SECRET_KEY")
url = "https://apiv2.bitcoinaverage.com/websocket/get_ticket"
print('public key: ' + publicKey)
print('secret key: ' + secretKey)
timestamp = int(time.time())
payload = '{}.{}'.format(timestamp, publicKey)
hex_hash = hmac.new(secretKey.encode(), msg=payload.encode(), digestmod=hashlib.sha256).hexdigest()
signature = '{}.{}'.format(payload, hex_hash)
ticket_url = "https://apiv2.bitcoinaverage.com/websocket/get_ticket"
ticket_header = {"X-signature": signature}
ticket = requests.get(url=ticket_url, headers=ticket_header).json()["ticket"]
print('ticket received: ' + ticket)
url = "wss://apiv2.bitcoinaverage.com/websocket/ticker?public_key={}&ticket={}".format(publicKey, ticket)
ws = websocket.create_connection(url)
subscribe_message = json.dumps({
		"event": "message",
		"data": {
			"operation": "subscribe",
			"options": {
				"currency": "BTCUSD",
				"market": "local"
			}
		}
	})
ws.send(subscribe_message)
while True:
    result = ws.recv()
    str = prettyJson(json.loads(result))
    print(str)
