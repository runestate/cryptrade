(
	set -x &&
	(
		(
			(ps aux | grep SCREEN | grep -v grep) && echo 'ERROR: one or more screens are already running' && exit 1
		) || true
	) &&
	(test "$1" || (echo 'missing param' && exit 1)) &&
	eval $(cat "$1" | grep = ) &&
	cd "$DEPLOY_DIRPATH" &&
	screen -dmS fetch bash -c 'cd fetch && ./fetch_app.sh; exec sh' &&
	screen -dmS parse bash -c 'cd parse && ./parse_app.sh; exec sh' &&
	screen -dmS watch bash -c 'cd watch && ./watch_app.sh; exec sh' &&
	screen -dmS alert bash -c 'cd alert && ./alert_app.sh; exec sh' &&
	screen -dmS s3push bash -c 'cd aws && ./upload_data_response_loop.sh ../config.ini; exec sh' &&
	echo 'done'
)