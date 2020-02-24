 aws s3api list-objects --bucket cryptrade --output json --query '[sum(Contents[].Size), length(Contents[])]'
