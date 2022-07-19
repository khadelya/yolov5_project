#!/usr/bin/env bash

set -e

currentVersion=$(git rev-parse HEAD)
docker build \
	-f Dockerfile \
	-t "adelya/yolo:${currentVersion}" \
	-t latest \
	.
