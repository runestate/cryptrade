import sys; 
sys.path.append('../fetch')
sys.path.append('../python')
import re
from core import NetworkExpert, AppConfig, OsExpert
from app import App
import logging
from threading import Thread
from datetime import datetime
from applogging import Log

class LogWatchPipeApp(App):
	def __init__(self):
		super().__init__(__file__, isToNotifyStartup = False)
		self.maxEmailReccurenceMinutes = float(AppConfig.setting('LOGWATCH_EMAIL_MAX_RECCURENCE_MINUTES'))
		self.triggerLines = ['ERROR', 'WARNING'] 
		Log.d('construct: {}', self.__dict__)		
		self.matchCountSinceLastEmail = 0
		self.lastEmailDatetime = None
	def email_maybe(self, header, message):
		now = datetime.now()
		if self.lastEmailDatetime is not None:
			minutesSinceLastEmail = (now - self.lastEmailDatetime).total_seconds() / 60.0 
			if minutesSinceLastEmail < self.maxEmailReccurenceMinutes:
				timeLeftMinutes = int(self.maxEmailReccurenceMinutes - minutesSinceLastEmail)
				Log.d('Aborting email notification ({}+ minutes left in window)', timeLeftMinutes)
				return
		self.lastEmailDatetime = now
		self.matchCountSinceLastEmail = 0
		NetworkExpert.tryAppNotifyByEmail(header, message)
	def run(self):
		emailHeader = 'LogWatchPipeApp input trigger match'
		while True:
			sys.stdout.flush()
			try:
				line = sys.stdin.readline()
			except KeyboardInterrupt:
				break	
			if not line:
				break
			sys.stdout.write(line)
			for triggerLine in self.triggerLines:
				if triggerLine in line:
					self.matchCountSinceLastEmail += 1
					Log.i('Log watch triggered, will send email')
					msg = 'The following line matched a trigger:\n\n{}\n\nMatches since last email attempt: {}\n\nNo more matches will be reported for {} minutes'.format(line, self.matchCountSinceLastEmail, self.maxEmailReccurenceMinutes)
					Thread(target=self.email_maybe, args=(emailHeader, msg)).start()
if __name__ == '__main__':
	LogWatchPipeApp().run()
