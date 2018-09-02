#!/bin/bash

# Exit this script if any error is encountered
set -e

# Execute inside this script directory
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

docker build -t opp ./Docker/

# docker run -p 127.0.0.1:8000:8000 -it --privileged -v "$DIR":/openParl opp 
docker run -p 80:8000 -it --privileged -v "$DIR":/openParl opp 
# /bin/bash -c 'cd openParl; ./runserver.sh; bash'
