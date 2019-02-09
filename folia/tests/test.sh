#!/bin/bash

if [ ! -z "$1" ]; then
    PYTHON=$1
else
    PYTHON=python
fi

if [ ! -z "$2" ]; then
    TESTDIR="$2"
else
    TESTDIR=`dirname $0`
fi
cd $TESTDIR

GOOD=1

echo "Testing main library">&2
$PYTHON maintest.py
if [ $? -ne 0 ]; then
    echo "Test failed!!!" >&2
    GOOD=0
fi

echo "Testing FQL">&2
$PYTHON fql.py
if [ $? -ne 0 ]; then
    echo "Test failed!!!" >&2
    GOOD=0
fi

echo "Testing all examples">&2
$PYTHON testallexamples.py
if [ $? -ne 0 ]; then
    echo "Test failed!!!" >&2
    GOOD=0
fi

cd ..

if [ $GOOD -eq 1 ]; then
    echo "Done, all tests passed!" >&2
    exit 0
else
    echo "TESTS FAILED!!!!" >&2
    exit 1
fi



