#!/bin/bash
cd /app

get_command() {
    sed -n -e "s/^$1://p" Procfile
}

if [ "$MERGIFYENGINE_INTEGRATION_ID" ]; then
  case $1 in
      web|worker) exec $(get_command $1);;
      aio) exec honcho start;;
  esac
fi
echo "usage: $0 (web|worker|aio)"
exit 1