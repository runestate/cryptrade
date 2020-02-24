(
	(test "$1" || (echo 'missing param' && exit 1)) &&
	while : 
	do		
		printf '.'
		./upload_data_response.sh "$1" 
		sleep 3600s			
    done
)
