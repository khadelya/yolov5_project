#!/usr/bin/env bash

set -e

docker run \
	--rm \
	-ti \
	--mount type=bind,source="$(pwd)/test_data",target="/usr/src/app" \
	"adelya/yolo:latest" \
	bash
