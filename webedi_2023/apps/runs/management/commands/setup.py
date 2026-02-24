import json
import re
from csv import reader
from urllib.parse import urlparse

from django.core.management import BaseCommand
from django.db import IntegrityError
from django.db.models import Q
from spices.django3.coreobjects.models import Vendor, VendorGroup

from apps.definitions.models import (
    Channel,
    Connector,
    ConnectorVendorInfo,
    ConnectorCapability,
    ConnectorCapabilityTypes,
)
from apps.runs.management.commands import LOGGER


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--setup_file",
            action="store",
            dest="setup_file",
            default=None,
            help=".csv file path",
        )

    def handle(self, *args, **options):
        LOGGER.info(f'Processing file: {options.get("setup_file")}')
        setup_list = read_csv_file(f'{options.get("setup_file")}')
        LOGGER.info(f"{setup_list}")

        for setup in setup_list:
            try:
                connector = setup_connector(setup=setup)
                setup_connector_vendor_info(setup=setup, connector=connector)

                setup_connector_capabilities(setup=setup, connector=connector)

            except IntegrityError as integrity_error:
                LOGGER.error(f"{integrity_error}")

        LOGGER.info(f"Finished command for the setup file")


def read_csv_file(file_path: str) -> list:
    connector_list = []
    with open(file_path, "r") as read_obj:
        csv_reader = reader(read_obj)
        header = next(csv_reader)
        LOGGER.info(f"Headers: {header}")

        if header is not None:
            for row in csv_reader:
                transformed_row = parse_csv_content(row)
                if transformed_row:
                    connector_list.append(transformed_row)

    return connector_list


def parse_csv_content(row: list):
    transformed_row = []
    for index, cell in enumerate(row):
        if not cell and index not in (2, 4, 5):
            LOGGER.error(f"row[{index}]: {cell}")
            return False
        transformed_row.append(cell.strip())
    return transformed_row


def get_code(code: str):
    transformed_code = re.sub("[ .,&]", "_", code.strip()).lower()
    transformed_code = transformed_code.replace("__", "_")
    transformed_code = re.sub("^_|_$", "", transformed_code)

    return transformed_code


def get_domain_from_url(url: str) -> str:
    parsed_uri = urlparse(url=url)
    return "{uri.scheme}://{uri.netloc}/".format(uri=parsed_uri)


def setup_connector(setup: list):
    code = get_code(setup[0])
    url_domain = get_domain_from_url(setup[1])
    connectors_with_same_login_url = Connector.objects.filter(
        Q(login_url=setup[1]) | Q(login_url__contains=url_domain)
    )

    if connectors_with_same_login_url:
        LOGGER.info(f"[Exists] Connector: {connectors_with_same_login_url}")
        return None

    connector = Connector.objects.get_or_create(
        adapter_code=code,
        name=setup[0],
        login_url=setup[1],
        channel=Channel.WEB,
        registration_url=setup[2],
        enabled=False,
        type=setup[3].upper(),
        icon=None,
    )
    LOGGER.info(f"[Success] Connector: {setup[0]}: {setup[3]}: {setup[1]}")
    return connector[0]


def setup_connector_vendor_info(setup: list, connector):
    if not connector:
        LOGGER.info(f"[Failed] Connector Vendor Info: Connector: {connector}")
        return None

    if setup[4] or setup[5]:
        vendor = int(setup[4]) if setup[4] else None
        vendor_group = int(setup[5]) if setup[5] else None

        if vendor:
            vendor = Vendor.try_retrieve(request=None, pk=vendor, cache_locally=True)

        if vendor_group:
            vendor_group = VendorGroup.try_retrieve(
                request=None, pk=vendor_group, cache_locally=True
            )

        vendor_connection_info = ConnectorVendorInfo.objects.get_or_create(
            connector_id=connector.id,
            vendor=vendor,
            vendor_group=vendor_group,
            requires_account_number=json.loads(setup[6].lower()),
            contains_support_document=json.loads(setup[7].lower()),
        )

        vendor_connection_info[0].save()
        LOGGER.info(f"[Success] Connector Vendor Info: {connector.id}: {setup[0]}")

        return vendor_connection_info[0]

    LOGGER.info(
        f"[Skipped] Connector Vendor Info: {connector.id}: {setup[0]} "
        f"since both vendor_id & vendor_group_id cannot be NONE"
    )
    return None


def setup_connector_capabilities(setup: list, connector):
    if not connector:
        LOGGER.info(f"[Failed] Connector capability setup: Connector: {connector}")
        return None
    connector_capability = list()
    try:
        capability = ConnectorCapabilityTypes.from_ident(setup[8].lower())
        connector_capability = ConnectorCapability.objects.get_or_create(
            connector=connector, type=capability, supported_file_format=setup[11]
        )
    except ValueError as exc:
        LOGGER.info(
            f"[Failed] Connector Capability:"
            f" Connector: {connector.id}: {setup[0]}: {setup[8]}: {setup[11]} with exception : {exc}"
        )

    LOGGER.info(
        f"[Success] Connector Capability : {connector.id}: {setup[0]}: {setup[8]}: {setup[11]}"
    )
    return connector_capability
