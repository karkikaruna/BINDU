#!/usr/bin/env bash
# Put this file in the bindu/ root.  First time only: chmod +x start.sh
# Run: ./start.sh            -> backend + mobile
#      ./start.sh backend    -> backend only
#      ./start.sh mobile     -> mobile only
set -e
cd "$(dirname "$0")"

backend() { (cd backend && python run.py); }
mobile()  { (cd mobile && npx expo start -c); }

case "${1:-all}" in
  backend) backend ;;
  mobile)  mobile ;;
  all)     backend & mobile; wait ;;
  *)       echo "Usage: ./start.sh [backend|mobile]"; exit 1 ;;
esac