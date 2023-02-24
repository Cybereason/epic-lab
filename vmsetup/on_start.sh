#!/bin/bash
set -u
set -e

# wait for creds
until gcloud auth list 2>/dev/null | grep developer.gserviceaccount.com || (( count++ >= 40 )); do
	echo "compute service account creds not ready yet"
	sleep 30s
done

# include
source <(gsutil cat "$gs_base_path/common.sh")


# script

echo "epic-lab: starting on-start script"

echo "epic-lab: on-start script done successfully"
