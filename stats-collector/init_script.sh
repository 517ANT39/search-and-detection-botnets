#!/bin/bash

mkdir -p models
protoc --proto_path=../proto --python_out=./models common.proto traffic_send_analyze.proto host_info.proto