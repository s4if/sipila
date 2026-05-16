#!/usr/bin/env bash
CONTAINER_ID=$1

if [ -z "$CONTAINER_ID" ]; then
  echo "Error: Container ID is required"
  exit 1
fi

docker exec $CONTAINER_ID /bin/bash -c "
  flask --app app db migrate
  flask --app app db upgrade
"
