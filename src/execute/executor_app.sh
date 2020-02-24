(
	app='executor_app.py'
	set -x &&
	python3 "$app" $1 |  ../bash/color.sh 
)
