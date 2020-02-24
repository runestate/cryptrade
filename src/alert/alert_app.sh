(
	app='alert_app.py'
	set -x &&
	python3 "$app" |  
	python3 ../logwatch/logwatchpipe.py |
	../bash/color.sh 
)
