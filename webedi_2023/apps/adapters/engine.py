import copy
import os

from django.conf import settings
from spices.django3.issues.models import IssueRule

from apps.adapters import LOGGER
from apps.adapters.accounting.r365 import R365Runner
from apps.adapters.accounting.r365_api import R365APIRunner
from apps.adapters.accounting.r365_sync import R365SyncRunner, R365PaymentsRunner
from apps.adapters.base import (
    AccountingPaymentUpdateInterface,
    AccountingSyncInterface,
    TEMP_DOWNLOAD_DIR,
)
from apps.adapters.base import PaymentInformationImportInterface
from apps.adapters.file_actions import SkipProcessing
from apps.adapters.framework.registry import connectors
from apps.adapters.helpers.webdriver_helper import DriverFactory
from apps.adapters.mock import MockVendorConnector
from apps.adapters.payment.ftp_payments import FTPPayment
from apps.adapters.vendors.alsco import AlscoRunner
from apps.adapters.vendors.athens_services import AthensServicesRunner
from apps.adapters.vendors.att import ATTRunner
from apps.adapters.vendors.baldor import BaldorRunner
from apps.adapters.vendors.bill_trust import BillTrustRunner
from apps.adapters.vendors.blue_shield import BlueShieldRunner
from apps.adapters.vendors.centerpoint_energy import CenterPointEnergyRunner
from apps.adapters.vendors.chefs_warehouse import ChefsWarehouseRunner
from apps.adapters.vendors.cig_insurance import CapitalInsuranceGroupRunner
from apps.adapters.vendors.cintas import CintasRunner
from apps.adapters.vendors.comcast import ComcastRunner
from apps.adapters.vendors.craft_beer_guild_distributing import (
    CraftBeerGuildDistributingRunner,
)
from apps.adapters.vendors.doordash import DoorDashRunner
from apps.adapters.vendors.duke_energy import DukeEnergyRunner
from apps.adapters.vendors.edward_don_and_co import EdwardDonRunner
from apps.adapters.vendors.efleets import EfleetsRunner
from apps.adapters.vendors.filpac import FilpacRunner
from apps.adapters.vendors.fintech import FintechRunner
from apps.adapters.vendors.frontier import FrontierRunner
from apps.adapters.vendors.granites_payment_portal import GranitesPaymentPortalRunner
from apps.adapters.vendors.ipfone import IpfoneRunner
from apps.adapters.vendors.kansas_gas_service import KansasGasServiceRunner
from apps.adapters.vendors.mid_american_energy_services import (
    MidAmericanEnergyServicesRunner,
)
from apps.adapters.vendors.nuco2 import NuCO2Runner
from apps.adapters.vendors.nv_energy import NVEnergyRunner
from apps.adapters.vendors.pge_company import PgECompanyRunner
from apps.adapters.vendors.pitney_bowes import PitneyBowesRunner
from apps.adapters.vendors.republic_services import RepublicServicesRunner
from apps.adapters.vendors.restaurant_depot import RestaurantDepotRunner
from apps.adapters.vendors.restaurant_technologies_inc import (
    RestaurantTechnologiesIncRunner,
)
from apps.adapters.vendors.shamrockfoods_company import ShamRockCompanyRunner
from apps.adapters.vendors.sherwin_williams import SherwinWilliamsRunner
from apps.adapters.vendors.singing_river import SingingRiverRunner
from apps.adapters.vendors.slemco import SlemcoRunner
from apps.adapters.vendors.smart_food_service import SmartFoodServiceRunner
from apps.adapters.vendors.socal_gas import SoCalGasRunner
from apps.adapters.vendors.southern_california_edison import (
    SouthernCaliforniaEdisonRunner,
)
from apps.adapters.vendors.southern_wine_online import SouthernWineOnlineRunner
from apps.adapters.vendors.southwest_gas import SouthWestGasRunner
from apps.adapters.vendors.sysco_account_center import SyscoAccountCenterRunner
from apps.adapters.vendors.term_sync import TermSyncRunner
from apps.adapters.vendors.tiger_natural_gas import TigerNaturalGasRunner
from apps.adapters.vendors.tpx_communications import OneCentralTPXRunner
from apps.adapters.vendors.unfi import UnfiRunner
from apps.adapters.vendors.us_foods import UsFoodsRunner
from apps.adapters.vendors.waste_management import WasteManagementRunner
from apps.adapters.vendors.water_district import WaterDistrictRunner
from apps.adapters.vendors.wbmason import WBMasonRunner
from apps.adapters.vendors.webstaurant_store import TheWebstaurantStoreRunner
from apps.definitions.models import ConnectorType, ConnectorCapabilityTypes
from apps.runs.models import Run, VendorPayment, PaymentStatus
from apps.utils.billpay_api import BillPayCoreClient

RUNNER_CLASSES = {
    "mock": MockVendorConnector,
    "bill_trust": BillTrustRunner,
    "southern_wine_online": SouthernWineOnlineRunner,
    "sysco_account_center": SyscoAccountCenterRunner,
    "term_sync": TermSyncRunner,
    "cintas": CintasRunner,
    "restaurant_depot": RestaurantDepotRunner,
    "doordash": DoorDashRunner,
    "efleets": EfleetsRunner,
    "us_foods": UsFoodsRunner,
    "singingriver": SingingRiverRunner,
    "smart_food_service": SmartFoodServiceRunner,
    "blue_shield": BlueShieldRunner,
    "las_vegas_valley_water_district": WaterDistrictRunner,
    "nv_energy": NVEnergyRunner,
    "pitney_bowes": PitneyBowesRunner,
    "granites_payment_portal": GranitesPaymentPortalRunner,
    "republic_services_inc": RepublicServicesRunner,
    "southwest_gas": SouthWestGasRunner,
    "cig_insurance": CapitalInsuranceGroupRunner,
    "tiger_natural_gas": TigerNaturalGasRunner,
    "socal_gas": SoCalGasRunner,
    "southern_california_edison": SouthernCaliforniaEdisonRunner,
    "shamrockfoods_company": ShamRockCompanyRunner,
    "webstaurant_store": TheWebstaurantStoreRunner,
    "frontier": FrontierRunner,
    "restaurant_technologies_inc": RestaurantTechnologiesIncRunner,
    "athensservice": AthensServicesRunner,
    "att": ATTRunner,
    "ipfone": IpfoneRunner,
    "unfi": UnfiRunner,
    "nuco2": NuCO2Runner,
    "alsco": AlscoRunner,
    "baldor": BaldorRunner,
    "wbmason": WBMasonRunner,
    "slemco": SlemcoRunner,
    "one_central_tpx": OneCentralTPXRunner,
    "craft_beer_guild_distributing": CraftBeerGuildDistributingRunner,
    "mid_american_energy_services": MidAmericanEnergyServicesRunner,
    "sherwin_williams": SherwinWilliamsRunner,
    "centerpoint_energy": CenterPointEnergyRunner,
    "chefs_warehouse": ChefsWarehouseRunner,
    "pge_company": PgECompanyRunner,
    "filpac": FilpacRunner,
    "comcast": ComcastRunner,
    "fintech": FintechRunner,
    "edward_don_and_co": EdwardDonRunner,
    "kansas_gas_service": KansasGasServiceRunner,
    "waste_management": WasteManagementRunner,
    "duke_energy": DukeEnergyRunner,
}


def get_vendor_runner(run: Run):
    """
    Factory for generating Runners
    :param run: Run
    :return: An object of a subclass of RunnerInterface to enable crawling/parsing a Connector
    """
    adapter_code = run.job.connector.adapter_code

    runner_cls = RUNNER_CLASSES.get(adapter_code)
    if runner_cls:
        return runner_cls(run=run)

    runner_cls = connectors.get(adapter_code, None)
    if runner_cls:
        download_location = f"{TEMP_DOWNLOAD_DIR}/runs/{run.id}"
        driver = DriverFactory.new(
            download_location=download_location,
            is_angular=getattr(runner_cls, "is_angular", False),
            uses_proxy=getattr(runner_cls, "uses_proxy", False),
        )
        return runner_cls(run=run, driver=driver, download_location=download_location)

    raise ValueError(f"Unknown adapter: {adapter_code}")


def get_accounting_runner(run: Run) -> AccountingPaymentUpdateInterface:
    """
    Factory for generating Runners
    :param run: Run
    :return: An object of a subclass of RunnerInterface to enable crawling/parsing a AccountingSite
    """
    adapter_code = run.job.connector.adapter_code

    runner_classes = {
        "r365": R365Runner,
        "r365_v1": R365APIRunner,
    }

    runner_cls = runner_classes.get(adapter_code)
    if runner_cls:
        return runner_cls(run)

    raise ValueError(f"Unknown adapter: {adapter_code}")


def _get_ftp_runner(run: Run) -> PaymentInformationImportInterface:
    adapter_code = run.job.connector.adapter_code

    runner_classes = {"FTP": FTPPayment}

    runner_cls = runner_classes.get(adapter_code)
    if runner_cls:
        return runner_cls(run)

    raise ValueError(f"Unknown adapter: {adapter_code}")


def _get_accounting_importer_runner(run: Run) -> AccountingSyncInterface:
    """
    Factory for generating Runners
    :param run: Run
    :return: An object of a subclass of RunnerInterface to enable crawling/parsing a AccountingSite
    """
    adapter_code = run.job.connector.adapter_code

    runner_classes = {
        "r365": R365SyncRunner,
        "r365_v1": R365SyncRunner,
    }

    runner_cls = runner_classes.get(adapter_code)
    if runner_cls:
        return runner_cls(run)

    raise ValueError(f"Unknown adapter: {adapter_code}")


def crawl_accounting_operation(run):
    check_runs = []
    adapter_code = run.job.connector.adapter_code
    import_entities = run.request_parameters.get("import_entities")
    import_payments = run.request_parameters.get(
        "import_payments"
    ) and import_entities == ["payment"]

    if import_entities:
        if import_payments and adapter_code == "r365_v1":
            runner = R365PaymentsRunner(run)
            runner.start_payment_import_flow(run)
        else:
            runner = _get_accounting_importer_runner(run)
            runner.start_sync_flow(run)
    if "accounting" in run.request_parameters:
        runner = get_accounting_runner(run)
        if run.dry_run:
            runner.login_flow(run)
        else:
            check_runs = runner.start_payment_update_flow(run)
    post_accounting_crawl(check_runs)


def connector_capabilities(run):
    """
    This function does operations as per connector capabilities
    """
    capability = run.action
    return {
        ConnectorCapabilityTypes.PAYMENT__EXPORT_INFO: _export_payments,
        ConnectorCapabilityTypes.PAYMENT__IMPORT_INFO: _import_payments,
        ConnectorCapabilityTypes.INVOICE__DOWNLOAD: _import_invoices,
    }.get(capability, "Not a valid capability")(run)


def _import_invoices(run):
    runner = get_vendor_runner(run)
    runner.start_documents_download_flow(run)
    if run.request_parameters.get("suppress_invoices", False):
        LOGGER.info(
            f"[tag:WEADENCR40][run:{run.id}] "
            f"Run on boarding steps are incomplete, post-process api is not called from FE yet.",
            exc_info=False,
        )
    else:
        post_process_discovered_files(run)


def _import_payments(run):
    runner = _get_ftp_runner(run=run)
    runner.start_payment_import_flow()
    post_process_discovered_files(run)


def _export_payments(run):
    runner = get_vendor_runner(run)
    runner.start_payment_flow(run)
    process_vendor_payments(run)


def crawl_vendor_operation(run):
    if run.dry_run:
        runner = get_vendor_runner(run)
        runner.login_flow(run)
    else:
        connector_capabilities(run)


def crawl_operations(operator, run):
    """
    This function does crawl operations as per connector type
    """
    return {
        ConnectorType.VENDOR.ident: crawl_vendor_operation,  # pylint: disable=no-member
        ConnectorType.ACCOUNTING.ident: crawl_accounting_operation,  # pylint: disable=no-member
    }.get(operator, "Not a valid operation")(run)


def crawl(run: Run):  # pylint: disable=too-many-branches
    """
    Entry point to start crawling for a specific run. This requires a valid Run object
    with corresponding fields (in this and all referenced objects) correctly set.
    """
    run.record_execution_start()
    try:
        crawl_operations(run.job.connector.type, run)
        run.record_success()
    except Exception as exc:  # pylint: disable=broad-except
        run.record_failure(exc)
        run.refresh_from_db()

        if not run.failure_issue:
            # if this exception could not be categorized, then raise
            LOGGER.exception(
                f"[tag:WEADENCR10][run:{run.id}] Caught an unexpected exception while executing run"
            )
            raise

        rule: IssueRule = IssueRule.objects.filter(code=run.failure_issue.code).first()
        if not rule or not rule.action_required:
            # if this exception has no rule set for it (ot action is not set) then raise
            LOGGER.exception(
                f"[tag:WEADENCR20][run:{run.id}] Caught a known exception while executing run,"
                f" but no rule is set to handle it"
            )
            raise

        # otherwise, the exception we just caught is a known one, so we don't
        # need to raise it. We'll just log what happened and move on.
        LOGGER.warning(
            f"[tag:WEADENCR30][run:{run.id}] Caught an exception while executing run, "
            f"error code: '{run.failure_issue.code}', rule: {rule.id} (action_required:{rule.action_required}).",
            exc_info=True,
        )


def process_payments(run: Run):
    try:
        run.record_execution_start()
        runner = _get_ftp_runner(run=run)
        runner.start_payment_import_flow()
        run.record_success()
    except Exception as ex:  # pylint: disable=broad-except
        LOGGER.exception(
            f"[tag:WEADENCR220][run:{run.id}] Caught a known exception while executing run"
            f" but no rule is set to handle it. Exception: {ex}"
        )
        run.record_failure()


def post_process_discovered_files(run: Run):
    from apps.adapters import file_actions  # pylint: disable=import-outside-toplevel

    discovered_files = run.discovered_files.all()
    failed_dfs = []
    run_id = run.id
    for discovered_file in discovered_files:
        try:
            action = file_actions.factory(discovered_file)
            LOGGER.info(
                f"[tag:INTADENG10][run:{run_id}][df:{discovered_file.id}] Performing action {action}"
            )

            action.execute()
        except SkipProcessing as exc:
            LOGGER.warning(
                f"[tag:INTADENG15][run:{run_id}][df:{discovered_file.id}] "
                f"Skipping processing discovered file"
            )
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error(
                f"[tag:INTADENG20][run:{run_id}][df:{discovered_file.id}] Unexpected exception: {str(exc)}",
                exc_info=True,
            )
            failed_dfs.append(discovered_file)

        # Delete local DFs after we're done with them
        try:
            if discovered_file.local_filepath and os.path.exists(
                discovered_file.local_filepath
            ):
                os.remove(discovered_file.local_filepath)
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.exception(
                f"[tag:INTADENG25][run:{run_id}][df:{discovered_file.id}] "
                f"Unexpected exception deleting file: {str(exc)}"
            )

    if failed_dfs:
        raise Exception(
            f"[tag:INTADENG30][run:{run_id}] Post processing "
            f"for the following discovered files failed: {[d.id for d in failed_dfs]}"
        )


def post_accounting_crawl(check_runs: list):
    failed_check_runs = []
    for check_run in check_runs:
        try:
            if check_run.is_checkrun_success:
                check_run.notify_export_success()

        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error(
                f"[CheckRun:{check_run.check_run_id}] Unexpected exception: {str(exc)}",
                exc_info=True,
            )
            failed_check_runs.append(check_run)

    if failed_check_runs:
        raise Exception(
            f"Post processing for the following CheckRuns failed: "
            f"{[cr.check_run_id for cr in failed_check_runs]}"
        )


def process_vendor_payments(run: Run):
    vendor_payments = VendorPayment.objects.filter(
        run=run, payment_status=PaymentStatus.SUCCESS
    )
    failed_vendor_payments = []
    for vendor_payment in vendor_payments:
        try:
            payment_details = copy.deepcopy(vendor_payment.payment_details)
            # updating bill-pay notes
            billpay_payment_id = payment_details["billpay_payment_id"]
            update_notes_response = BillPayCoreClient(
                settings.BILL_PAY_SERVER_URL, settings.BILL_PAY_CLIENT_TOKEN
            ).update_notes_for_payment(billpay_payment_id, payment_details["notes"])
            payment_details["update_notes_response"] = update_notes_response
            # updating bill-pay status
            update_status_response = BillPayCoreClient(
                settings.BILL_PAY_SERVER_URL, settings.BILL_PAY_CLIENT_TOKEN
            ).update_payment_status(billpay_payment_id)
            # updating the response of both the api calls
            payment_details["update_status_response"] = update_status_response
            vendor_payment.payment_details = payment_details
            vendor_payment.save()
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.error(
                f"[VendorPayment:{vendor_payment.id}] Unexpected exception: {str(exc)}",
                exc_info=True,
            )
            failed_vendor_payments.append(vendor_payment)

    if failed_vendor_payments:
        raise Exception(
            f"Post processing for the following vendor_payments failed: "
            f"{[vp.id for vp in failed_vendor_payments]}"
        )
