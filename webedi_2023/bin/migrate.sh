#!/usr/bin/env bash

PENDING_MIGRATIONS=`python manage.py showmigrations | grep '\[ \]'`

if [ "x$DEPLOY_AUTOMIGRATE_ENABLED" == "x" ]; then
    echo $PENDING_MIGRATIONS

    if [ -z "$PENDING_MIGRATIONS" ]; then
        echo "No migrations"
    else
        echo "Pending migrations"
        exit 255;
    fi
else
    echo $PENDING_MIGRATIONS

    if [ -z "$PENDING_MIGRATIONS" ]; then
        echo "No migrations"
    else
        # run any migrations on test server
        python manage.py migrate --noinput
    fi

fi
