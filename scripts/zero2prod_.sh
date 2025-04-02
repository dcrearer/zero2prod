#!/usr/bin/env bash

podman run -it --name zero2prod --rm -p 8000:8000 -v /Users/crearerd/Dev/rust/<>:/app/configuration zero2prod:latest | bunyan
