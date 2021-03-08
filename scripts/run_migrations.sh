#!/bin/bash

RESULT=$(python3.8 ${APP_HOME}/manage.py check_migrations)

if [ "$RESULT" = "True" ]; then
    echo "Migration already executed."
else
    python3.8 ${APP_HOME}/manage.py migrate_schemas --noinput
fi
