import sys; 
sys.path.append('../fetch')
sys.path.append('../python')
from core import OsExpert, AppConfig, StringExpert 
from app import App
from applogging import Log
import aiohttp
import asyncio
import async_timeout
import re
import html
import time
import json

class AlertApp(App):
	def __init__(self):
		super().__init__(__file__)
		Log.d('construct')
	def run(self, alert_interval_seconds):	
			Log.i('Check interval is: {} seconds', alert_interval_seconds)
			loop = asyncio.get_event_loop()
			loop.run_until_complete(
				self.alert_continuously(alert_interval_seconds)
				)
	async def alert_continuously(self, alert_interval_seconds):	
		is_triggered = False
		while True: #is_triggered == False:
			try:
				is_triggered = await self.check_for_alert_match()
			except Exception as e:
				stacktrace = OsExpert.stacktrace()
				Log.e('Failed to run alert check, stacktace:\n{}', stacktrace)
			await asyncio.sleep(alert_interval_seconds)
	async def check_for_alert_match(self):
		urls = [
			'https://twitter.com/CFTC', 
			'https://twitter.com/sec_enforcement?lang=en',
			'https://twitter.com/ushouserep?lang=en'
			]
		strip_texts = None
		with open('ignore-lines.json', 'r') as f:    
		    strip_texts = json.load(f)			    	    
		Log.d('checking {} sources, ignoring {} lines..', len(urls), len(strip_texts))
		patterns = [
			r'.{,200}bitcoin.{,200}', 
			r'.{,200}crypto.{,200}', 
			r'.{,200}virtual currency.{,200}',
			]
		for url in urls:
			async with aiohttp.ClientSession() as session:
				html_text = await self.__fetch(session, url)
				text = StringExpert.strip_tags(html_text)
				text = html.unescape(text)
				for strip_text in strip_texts:
					text = text.replace(strip_text, '')
				for pattern in patterns:
					match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
					if match is not None:
						matched_line = match.group()
						warning = 'Found pattern "{}" at url "{}" in line: {}'.format(pattern, url, matched_line) 
						Log.w(warning)						
						return True
		return False
	async def __fetch(self, session, url):
		try:
			timeout_seconds = 20
			with async_timeout.timeout(timeout_seconds):
				async with session.get(url) as response:
					return await response.text()
		except Exception as e: 
			raise Exception('Failed to retrieve url "{}" using timeout {}'.format(url, timeout_seconds)) from e 

if __name__ == '__main__':
	try:
		app = AlertApp()
		app.run(
			alert_interval_seconds = 15
			)
	except KeyboardInterrupt:
		print('\n\nKeyboardInterrupt\n')
	except Exception as e:
		Log.c('app failed: {}', e)
		stacktrace = OsExpert.stacktrace()
		Log.d('stacktrace:\n{}', stacktrace)
