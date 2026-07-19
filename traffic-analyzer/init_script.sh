#!/bin/bash

mkdir -p src/gen/models
protoc --proto_path=../proto --python_out=./src/gen/models common.proto traffic_send_analyze.proto host_info.proto