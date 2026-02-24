import environ
from django.core.management.base import BaseCommand

from apps.definitions.models import Connector, ConnectorType
from apps.jobconfig.models import Job
from apps.runs.management.commands import LOGGER


class Command(BaseCommand):
    help = "create crawl env file for unit testing"

    # pylint: disable=no-member
    def handle(self, *args, **options):
        LOGGER.info("Beginning to get all vendor connectors")
        connectors = Connector.objects.filter(
            enabled=True,
            type=ConnectorType.VENDOR.value,  # pylint: disable=no-member
        )
        creds = dict()
        for connector in connectors:
            LOGGER.info(
                f"Copying login url for connector : {connector.id} with name : {connector.name}"
            )
            jobs = Job.objects.filter(connector_id=connector.id, enabled=True)
            for job in jobs:
                creds[connector.adapter_code] = {
                    "username": job.username,
                    "password": job.password,
                    "login_url": connector.login_url,
                }
                LOGGER.info(f"Recorded creds for connector : {connector.id}")

        with open(
            f"{str(environ.Path(__file__) - 3)}/local_crawler_env.env", "w"
        ) as file:
            for cred in creds:
                cred_data = creds[cred]
                cred_line = (
                    f"{cred}=username={cred_data['username']};"
                    f"password={cred_data['password']};"
                    f"login_url={cred_data['login_url']}\n"
                )
                LOGGER.info(f"Written : {cred_line} to the file")
                file.write(cred_line)
