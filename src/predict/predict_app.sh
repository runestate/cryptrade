(
	app='predict_app.py'
	set -x &&
	python3 "$app" $1 2>&1 |  ../bash/color.sh 
)
