#!/bin/sh

curl --fail -H 'Content-Type: application/json' \
    --data '{}' \
    http://localhost:${PORT:-3000}/$TOKEN || exit 1
