#!/bin/bash

pid=$(ps ax | grep node | grep serve_tests | grep -v grep | awk '{print $1}');
if [[ "$pid" != "" ]]; then
    #echo "Server already started."
    exit 0;
fi

dir=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

# Start the server (pipe output to server.log)
node ${dir}/serve_tests.js &> ${dir}/server.log &
pid=$!;

# Wait a second so the server has a chance to start.
sleep 1;

check=$(ps ax | grep ${pid} | grep -v grep);

if [[ "$check" == "" ]]; then
    echo "Server failed to start";
    exit 1;
else
    exit 0;
fi
