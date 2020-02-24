(
	set -x &&
	(test "$1" || (echo 'missing param' && exit 1)) &&
	eval $(cat "$1" | grep = ) &&
	test -d "$DATA_RESPONSE_DIRPATH" &&	
	cd "$DATA_RESPONSE_DIRPATH" &&
	s3path="$DATA_RESPONSE_S3_BUCKET_NAME/$DATA_RESPONSE_S3_BUCKET_PATH/" &&
	echo "Syncing from path: $s3path" &&
	aws s3 sync "s3://$s3path" . --include '*' &&
	printf "\n\nCount of bucket files synced\n:" &&
	aws s3 ls "s3://$s3path" --recursive | wc -l	
)
