#!/bin/bash

SERVER="$1"
shift
echo "$@"
CMD="sh run_bash.sh $@"
eb ssh "$SERVER" -e "ssh -tt -o StrictHostKeyChecking=no" -c "$CMD"
