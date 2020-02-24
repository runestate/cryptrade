(
	set -x &&
	(test "$1" || (echo 'missing param' && exit 1)) &&
	eval $(cat "$1" | grep = ) &&
	(test "$LOG_DIRPATH" || (echo 'ERROR: No log path' && exit 1)) &&
	latestLogFilepath="$LOG_DIRPATH/s3push.latest.log" &&
	historyLogFilepath="$LOG_DIRPATH/s3push.history.log" &&	
	(
		current_date_time=`date "+%Y-%m-%d %H:%M:%S"` &&
		echo '======================================' &&
		echo "=== S3 push at $current_date_time ===" &&
		echo '======================================' &&
		(
			test -d "$DATA_RESPONSE_DIRPATH" &&	
			cd "$DATA_RESPONSE_DIRPATH" &&
			s3path="$DATA_RESPONSE_S3_BUCKET_NAME/$DATA_RESPONSE_S3_BUCKET_PATH/" &&
			echo 'Generating zip file' &&
			filePattern='.*_[0-9]*[0-9]' &&
			# filenames=`find . -regex "$filePattern" -print` &&
			filenames=`find . -regextype posix-extended -regex '(.*_[0-9]*[0-9]|.+response)' -print` &&
			fileCount=`echo "${filenames}" | wc -l | tr -d '[:space:]'` &&
			timestamp=`date +%s` &&
			zipFilename="${timestamp}_${fileCount}.zip" &&
			echo "Moving $fileCount file(s) to zip file: $zipFilename" &&
			echo "$filenames" | zip -m "./$zipFilename" -@  &&
			echo "Syncing to path: $s3path" &&
			aws s3 sync . "s3://$s3path" --exclude '*' --include "*.zip" &&
			printf "\n\nBucket count\n:" &&
			aws s3 ls "s3://$s3path" --recursive | wc -l &&
			echo 'done!'
		) || echo 'Failed'
	) > "$latestLogFilepath" && 
	cat "$latestLogFilepath" >> "$historyLogFilepath" &&
	cat "$latestLogFilepath" &&
	echo "Log files written"
)