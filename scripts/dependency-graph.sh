#!/bin/bash

MAX_DEPTH=${1:-1}
cargo modules dependencies --lib --max-depth $MAX_DEPTH | dot -Tpng > module-deps.png
