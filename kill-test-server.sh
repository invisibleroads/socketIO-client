#!/bin/bash

pid=$(ps ax | grep node | grep serve_tests | grep -v grep | awk '{print $1}');
if [[ "$pid" == "" ]]; then
    echo "Server not started."
    exit 0;
fi

kill ${pid}

# Ensure it's dead... Jim
pid=$(ps ax | grep node | grep serve_tests | grep -v grep | awk '{print $1}');
if [[ "$pid" != "" ]]; then
    echo "Server didn't die :(."
    exit 1;
else
    exit 0;
fi
