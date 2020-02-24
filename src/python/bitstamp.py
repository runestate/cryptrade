import json
import time
import configparser
import io
import hashlib
import requests
import hmac
import websocket
import simplejson as json
from applogging import Log

config = configparser.ConfigParser()
config.read('config.ini')
configSettings = config["SETTINGS"]
publicKey = configSettings["BITCOINAVERAGE_PUBLIC_KEY"]
secretKey = configSettings["BITCOINAVERAGE_SECRET_KEY"]
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
    Log.d("Received '%s'" % prettyJson(json.loads(result)))
