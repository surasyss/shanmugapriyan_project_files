#!/bin/bash

## Start syslog to send logger data
rsyslogd

## Boot into virtualenv
. bin/activate

## Get config from Heroku and export it
spicli aws get-secrets --names "$ENV_CONFIG" --output .env_config
. .env_config

export

## Run migrate.sh to check migrations
bin/migrate.sh

if [[ "$?" != 0 ]]
then
exit "$?"
fi

chmod 777 /tmp
chmod 777 /var/tmp

## Boot into app as celery user.
su --preserve-environment -s /bin/bash -c '/app/bin/start-foreman' celery
