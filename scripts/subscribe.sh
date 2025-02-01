#!/usr/bin/env bash

SUBSCRIBE=~/Dev/rust/src/zero2prod/scripts/subscribe.json

newman run $SUBSCRIBE -n 1 --delay-request 5
