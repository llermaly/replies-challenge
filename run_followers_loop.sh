#!/bin/bash
cd "$(dirname "$0")"
while true; do python3 collect.py followers-only >> /tmp/tracker-followers.log 2>&1; sleep 3600; done
