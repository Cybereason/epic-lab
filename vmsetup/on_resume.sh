#!/bin/bash
set -u
set -e

# include
source <(gsutil cat "$gs_base_path/common.sh")


# script

echo "epic-lab: starting on-resume script"

echo "epic-lab: on-resume script done successfully"
