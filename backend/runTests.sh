#!/bin/bash
set -e

# Build and run tests
sudo docker build -t blnstats-backend "$(dirname "$0")"
sudo docker run --rm blnstats-backend python3 -m unittest discover -s tests -p "test_*.py"
