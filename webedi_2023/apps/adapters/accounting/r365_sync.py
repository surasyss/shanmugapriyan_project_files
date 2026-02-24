import abc
import json
import logging
import os
import uuid
from pathlib import Path
from typing import List

from spices.documents import DocumentType

from apps.adapters.accounting.r365_core import R365CoreClient
from apps.adapters.base import AccountingSyncInterface, TEMP_DOWNLOAD_DIR
from apps.adapters.framework import download
from apps.adapters.framework.download import download_discovered_file
from apps.definitions.models import EntityType
from apps.runs.models import (
    Run,
    DiscoveredEntity,
    ExportRequest,
    DiscoveredFile,
    FileFormat,
)
from apps.utils.piq_core import PIQCoreClient
from integrator.settings import PIQ_API_BASE_URL, PIQ_API_TOKEN

LOGGER = logging.getLogger("apps.adapters.accounting")


class R365Helper:
    @staticmethod
    def parse_bank_account_response(bank_account_response) -> List:
        filtered_response = []
        for bank_account in bank_account_response:
            filtered_response.append(
                {
                    "accounting_sw_id": None,
                    "id": bank_account.get("Id"),
                    "account_name": bank_account.get("AccountName"),
                    "account_number": bank_account.get("AccountNumber"),
                    "location": bank_account.get("Location"),
                    "last_reconciled_balance": bank_account.get(
                        "LastReconciledBalance"
                    ),
                    "last_reconciled_date": bank_account.get("LastReconciledDate"),
                    "next_check_number": bank_account.get("NextCheckNumber"),
                    "bank": bank_account.get("Bank"),
                    "bank_account_number": bank_account.get("BankAccountNumber"),
                    "bank_name": bank_account.get("BankName"),
                    "bank_user_name": bank_account.get("BankUserName"),
                    "routing_number": bank_account.get("RoutingNumber"),
                    "gl_account_id": bank_account.get("GLAccountId"),
                    "second_signature": bank_account.get("secondSignature"),
                    "second_signature_threshold": bank_account.get(
                        "secondSignatureThreshold"
                    ),
                }
            )
        return filtered_response

    @staticmethod
    def parse_vendor_response(vendor_response) -> List:
        filtered_response = []
        for vendor in vendor_response:
            filtered_response.append(
                {
                    "accounting_sw_id": None,
                    "name": vendor.get("Name"),
                    "account_id": vendor.get("Name"),
                    "street_address": f'{vendor.get("Street1")} {vendor.get("Street2")}',
                    "city": vendor.get("City"),
                    "state": vendor.get("State"),
                    "zipcode": vendor.get("Zip"),
                    "net_terms": vendor.get("PaymentTerm"),
                }
            )
        return filtered_response

    @staticmethod
    def parse_gl_account_response(gl_account_response) -> List:
        filtered_response = []
        for gl_account in gl_account_response:
            filtered_response.append(
                {
                    "gl_account_id": gl_account.get("GLAccountId"),
                    "account_name": gl_account.get("AccountName"),
                    "account_number": gl_account.get("AccountNumber"),
                    "gl_type": gl_account.get("GLType"),
                    "parent_account": gl_account.get("ParentAccount"),
                    "operational_report_category": gl_account.get(
                        "OperationalReportCategory"
                    ),
                    "available_to_managers": gl_account.get("AvailableToManagers"),
                    "description": gl_account.get("Description"),
                    "disable_entry": gl_account.get("DisableEntry"),
                    "percent_of": gl_account.get("PercentOf"),
                    "percent_of_account": gl_account.get("PercentOfAccount"),
                    "percent_of_type": gl_account.get("PercentOfType"),
                    "cash_flow_category": gl_account.get("CashFlowCategory"),
                    "is_statistical_account": gl_account.get("IsStatisticalAccount"),
                }
            )
        return filtered_response


class R365SyncRunner(AccountingSyncInterface):
    """
    Runner Class for Syncing Bank Accounts, Vendors,
    GL Accounts from R365 to PIQ Database
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.piq_client = PIQCoreClient(PIQ_API_BASE_URL, PIQ_API_TOKEN)
        self.r365 = R365CoreClient(self.run.job.login_url)
        self.r365_helper = R365Helper()
        self.entities_to_import = self.run.request_parameters["import_entities"]
        self.restaurant_ids = []
        self.company_ids = []
        self.piq_details = {}
        self.r365_details = {}

    def _r365_login(self):
        self.r365_details["session_id"] = self.r365.get_auth_credentials(
            self.run.job.username, self.run.job.password
        )
        self.r365_details["user_id"] = self.r365.get_session_data(
            self.r365_details["session_id"]
        )

    def _fetch_unique_restaurant_ids(self, company_ids: List[int]) -> List[int]:
        restaurant_ids = []
        for company_id in company_ids:
            json_response = self.piq_client.get_accounting_company_by_id(company_id)
            for restaurant in json_response["restaurants"]:
                restaurant_id = restaurant["id"]
                if restaurant_id not in restaurant_ids:
                    restaurant_ids.append(restaurant_id)

        return restaurant_ids

    def _get_all_rest_sub_accounts(self, company_id: int) -> List:
        json_response = self.piq_client.get_rest_sub_account(company=company_id)
        gl_account_list = json_response["results"]
        next_page = 1
        while json_response["next"]:
            next_page += 1
            json_response = self.piq_client.get_rest_sub_account(
                company=company_id, page=next_page
            )
            gl_account_list += json_response["results"]

        return gl_account_list

    # pylint: disable=no-member
    def _fetch_piq_details(self):
        """
        Fetches PIQ Details: Bank Accounts, Vendors, GL Accounts
        """
        companies = self.run.job.companies.all().values_list("remote_id", flat=True)

        if not companies:
            raise Exception(f"[tag:WEWARAC2] companies cannot be : None or Empty list")

        self.company_ids = list(companies)
        if EntityType.GL_ACCOUNT.ident in self.entities_to_import:
            gl_account_list = []
            for company_id in self.company_ids:
                json_response = self._get_all_rest_sub_accounts(company_id)
                gl_account_list += json_response
            self.piq_details[EntityType.GL_ACCOUNT.ident] = gl_account_list

        if EntityType.BANK_ACCOUNT.ident in self.entities_to_import:
            self.restaurant_ids = self._fetch_unique_restaurant_ids(self.company_ids)

    # pylint: disable=no-member
    def _fetch_r365_details(self):
        """
        Fetches R365 Details: Bank Accounts, Vendors, GL Accounts
        The API used here is paginated
        1st API call is to get the total count of the results
        2nd API call is to get all the results
        """
        if (
            EntityType.BANK_ACCOUNT.ident
            in self.run.request_parameters["import_entities"]
        ):
            json_response = self.r365.get_grid_source_request(
                grid_name="Bank+Accounts",
                filters=None,
                user_id=self.r365_details["user_id"],
                is_employee="AccountName",
                count="1",
            )
            json_response = self.r365.get_grid_source_request(
                grid_name="Bank+Accounts",
                filters=None,
                user_id=self.r365_details["user_id"],
                is_employee="AccountName",
                count=json_response[0]["__count"],
            )
            self.r365_details[
                EntityType.BANK_ACCOUNT.ident
            ] = self.r365_helper.parse_bank_account_response(json_response)

        if EntityType.VENDOR.ident in self.run.request_parameters["import_entities"]:
            json_response = self.r365.get_grid_source_request(
                grid_name="Vendors",
                filters=None,
                user_id=self.r365_details["user_id"],
                is_employee="Name%2CVendorGroup+desc",
                count="1",
            )
            json_response = self.r365.get_grid_source_request(
                grid_name="Vendors",
                filters=None,
                user_id=self.r365_details["user_id"],
                is_employee="Name%2CVendorGroup+desc",
                count=json_response[0]["__count"],
            )
            self.r365_details[
                EntityType.VENDOR.ident
            ] = self.r365_helper.parse_vendor_response(json_response)

        if (
            EntityType.GL_ACCOUNT.ident
            in self.run.request_parameters["import_entities"]
        ):
            json_response = self.r365.get_grid_source_request(
                grid_name="GL+Accounts",
                filters=None,
                user_id=self.r365_details["user_id"],
                is_employee="AccountNumber%2CAccountName",
                count="1",
            )
            json_response = self.r365.get_grid_source_request(
                grid_name="GL+Accounts",
                filters=None,
                user_id=self.r365_details["user_id"],
                is_employee="AccountNumber%2CAccountName",
                count=json_response[0]["__count"],
            )
            self.r365_details[
                EntityType.GL_ACCOUNT.ident
            ] = self.r365_helper.parse_gl_account_response(json_response)

    def _get_all_bank_accounts(self, restaurant_id: int) -> List:
        json_response = self.piq_client.get_accounting_bank_account(
            restaurant=restaurant_id
        )
        bank_account_list = json_response["results"]
        next_page = 1
        while json_response["next"]:
            next_page += 1
            json_response = self.piq_client.get_accounting_bank_account(
                restaurant=restaurant_id, page=next_page
            )
            bank_account_list += json_response["results"]

        return bank_account_list

    def _sync_bank_accounts(self, run: Run) -> List[DiscoveredEntity]:
        LOGGER.info(f"[tag:R365SBA10][run:{run.id}] Starting sync for bank accounts.")
        discovered_entities = []

        for restaurant_id in self.restaurant_ids:
            piq_bank_accounts = self._get_all_bank_accounts(restaurant_id)

            piq_id_num_name_tuple = {
                (
                    bank_account["accounting_sw_id"],
                    bank_account["account_number"],
                    bank_account["account_name"],
                )
                for bank_account in piq_bank_accounts
            }
            piq_id_num_tuple = {
                (bank_account["accounting_sw_id"], bank_account["account_number"])
                for bank_account in piq_bank_accounts
            }

            # Filtered List: R365 (Accounting SW ID, Account Number, Account Name) not present in PIQ List
            piq_filtered_list = [
                bank_account
                for bank_account in self.r365_details["bank_account"]
                if (
                    bank_account["accounting_sw_id"],
                    bank_account["account_number"],
                    bank_account["account_name"],
                )
                not in piq_id_num_name_tuple
            ]

            # Filtering the list of records to be created
            r365_create_list = [
                bank_account
                for bank_account in piq_filtered_list
                if (bank_account["accounting_sw_id"], bank_account["account_number"])
                not in piq_id_num_tuple
            ]
            LOGGER.info(
                f"[tag:R365SBA12][run:{run.id}] No of new accounts : {len(r365_create_list)}"
            )
            # Filtering the list of records to be updated
            r365_update_list = [
                bank_account
                for bank_account in piq_filtered_list
                if (bank_account["accounting_sw_id"], bank_account["account_number"])
                in piq_id_num_tuple
            ]
            LOGGER.info(
                f"[tag:R365SBA14][run:{run.id}] No of existing accounts : {len(r365_update_list)}"
            )

            if r365_create_list:
                discovered_entities += self.create_or_update_bank_acc(
                    run, restaurant_id, r365_create_list, True
                )

            if r365_update_list:
                discovered_entities += self.create_or_update_bank_acc(
                    run, restaurant_id, r365_update_list, False, piq_bank_accounts
                )
        LOGGER.info(f"[tag:R365SBA16][run:{run.id}] Completed sync for bank accounts")
        return discovered_entities

    def create_or_update_bank_acc(
        self,
        run: Run,
        restaurant_id: int,
        r365_bank_acc_list: list,
        create_or_update: bool,
        piq_bank_accounts: List = None,
    ) -> List[DiscoveredEntity]:
        LOGGER.info(
            f"[tag:R365SBACUBA10][run:{run.id}] Starting creating or updating bank accs"
        )
        discovered_entities = []
        for bank_account in r365_bank_acc_list:
            r365_account_number = bank_account["account_number"]
            r365_account_name = bank_account["account_name"]

            source_entity_id = f"{run.id}_{r365_account_number}_{restaurant_id}"
            LOGGER.info(
                f"[tag:R365SBACUBA12][run:{run.id}][SEI:{source_entity_id}] Creating export request."
            )

            export_request = ExportRequest(run=run)
            export_request.save()

            LOGGER.info(
                f"[tag:R365SBACUBA14][run:{run.id}][SEI:{source_entity_id}] Creating discovered entity."
            )
            discovered_entity = DiscoveredEntity(
                run=run,
                source_entity_id=source_entity_id,
                type=EntityType.BANK_ACCOUNT.ident,
                export_request=export_request,
            )
            discovered_entity.attrs = self.r365_details[EntityType.BANK_ACCOUNT.ident]
            discovered_entity.save()

            if create_or_update:
                LOGGER.info(
                    f"[tag:R365SBACUBA16][run:{run.id}][SEI:{source_entity_id}] "
                    f"Creating bank account."
                )
                json_response = self.piq_client.post_accounting_bank_account(
                    restaurant_id,
                    r365_account_number,
                    r365_account_name,
                    bank_account["accounting_sw_id"],
                    bank_account_type=1,
                )
            else:
                patch_id = next(
                    (
                        bank_account["id"]
                        for bank_account in piq_bank_accounts
                        if bank_account["account_number"] == r365_account_number
                    ),
                    None,
                )
                LOGGER.info(
                    f"[tag:R365SBACUBA16][run:{run.id}][SEI:{source_entity_id}][PATCH:{patch_id}] "
                    f"Updating bank account."
                )
                json_response = self.piq_client.patch_accounting_bank_account(
                    patch_id, restaurant=restaurant_id, account_name=r365_account_name
                )

            LOGGER.info(
                f"[tag:R365SGACUGA18][run:{run.id}][SEI:{source_entity_id}][ER:{export_request.id}]"
                f" Updating export_request."
            )
            export_request.http_request_url = json_response.url
            export_request.http_request_method = json_response.request.method
            export_request.http_request_json = json.loads(
                json_response.request.body.decode("utf8")
            )
            export_request.http_response_code = json_response.status_code
            export_request.http_response_body = json_response.text
            export_request.save()

            LOGGER.info(
                f"[tag:R365SGACUGA20][run:{run.id}][SEI:{source_entity_id}][DE:{discovered_entity.id}] "
                f"Updating discovered_entity."
            )
            discovered_entity.export_request = export_request
            discovered_entity.save()
            discovered_entities.append(discovered_entity)
        return discovered_entities

    def _sync_vendors(self, run: Run) -> List[DiscoveredEntity]:
        LOGGER.info(f"[tag:R365SVE10][run:{run.id}] Starting sync for vendors")
        discovered_entities = []

        for company_id in self.company_ids:
            source_entity_id = f"{run.id}_{company_id}"
            LOGGER.info(
                f"[tag:R365SVE12][run:{run.id}][SEI:{source_entity_id}] Creating export request."
            )
            export_request = ExportRequest(run=run)
            export_request.save()

            LOGGER.info(
                f"[tag:R365SVE12][run:{run.id}][SEI:{source_entity_id}] Creating discovered entity."
            )
            discovered_entity = DiscoveredEntity(
                run=run,
                source_entity_id=source_entity_id,
                type=EntityType.VENDOR.ident,
                export_request=export_request,
            )
            discovered_entity.attrs = self.r365_details[EntityType.VENDOR.ident]
            discovered_entity.save()

            LOGGER.info(
                f"[tag:R365SGACUGA20][run:{run.id}][SEI:{source_entity_id}] "
                f"Creating vendor account."
            )
            json_response = self.piq_client.post_acc_vendor_bulk_create(
                vendors=self.r365_details[EntityType.VENDOR.ident], company=company_id
            )

            LOGGER.info(
                f"[tag:R365SGACUGA30][run:{run.id}][SEI:{source_entity_id}][ER:{export_request.id}]"
                f" Updating export_request."
            )
            export_request.http_request_url = json_response.url
            export_request.http_request_method = json_response.request.method
            export_request.http_request_json = json.loads(
                json_response.request.body.decode("utf8")
            )
            export_request.http_response_code = json_response.status_code
            export_request.http_response_body = json_response.text
            export_request.save()

            LOGGER.info(
                f"[tag:R365SGACUGA30][run:{run.id}][SEI:{source_entity_id}][DE:{discovered_entity.id}] "
                f"Updating discovered_entity."
            )
            discovered_entity.export_request = export_request
            discovered_entity.save()
            discovered_entities.append(discovered_entity)
        return discovered_entities

    def _sync_gl_accounts(self, run: Run) -> List[DiscoveredEntity]:
        LOGGER.info(f"[tag:R365SGA10][run:{run.id}] Starting sync for gl accounts")
        discovered_entities = []

        piq_num_name_tuple = {
            (gl_account["account_number"], gl_account["account_name"])
            for gl_account in self.piq_details["gl_account"]
        }
        piq_num_tuple = {
            (gl_account["account_number"])
            for gl_account in self.piq_details["gl_account"]
        }
        piq_filtered_list = [
            gl_account
            for gl_account in self.r365_details["gl_account"]
            if (gl_account["account_number"], gl_account["account_name"])
            not in piq_num_name_tuple
        ]

        r365_create_list = [
            gl_account
            for gl_account in piq_filtered_list
            if (gl_account["account_number"]) not in piq_num_tuple
        ]
        LOGGER.info(
            f"[tag:R365SGA12][run:{run.id}] No of new accounts : {len(r365_create_list)}"
        )
        r365_update_list = [
            gl_account
            for gl_account in piq_filtered_list
            if gl_account["account_number"] in piq_num_tuple
        ]
        LOGGER.info(
            f"[tag:R365SGA14][run:{run.id}] No of existing accounts : {len(r365_update_list)}"
        )

        for piq_company_id in self.company_ids:
            LOGGER.info(
                f"[tag:R365SGA14][run:{run.id}] getting discovered entities for company : {piq_company_id}"
            )
            if r365_create_list:
                discovered_entities += self.create_or_update_gl_acc(
                    run, piq_company_id, r365_create_list, True
                )

            if r365_update_list:
                discovered_entities += self.create_or_update_gl_acc(
                    run,
                    piq_company_id,
                    r365_update_list,
                    False,
                    self.piq_details["gl_account"],
                )
        LOGGER.info(f"[tag:R365SGA20][run:{run.id}] Completed sync for gl accounts")
        return discovered_entities

    def create_or_update_gl_acc(
        self,
        run: Run,
        piq_company_id: int,
        r365_gl_acc_list: list,
        create_or_update: bool,
        piq_gl_accounts: List = None,
    ) -> List[DiscoveredEntity]:
        LOGGER.info(
            f"[tag:R365SGACUGA10][run:{run.id}] Starting creating or updating gl accs"
        )
        discovered_entities = []
        for gl_account in r365_gl_acc_list:
            r365_account_number = gl_account["account_number"]
            r365_account_name = gl_account["account_name"]

            source_entity_id = (
                f'{run.id}_{gl_account["gl_account_id"]}_{piq_company_id}'
            )
            LOGGER.info(
                f"[tag:R365SGACUGA12][run:{run.id}][SEI:{source_entity_id}] Creating export request."
            )

            export_request = ExportRequest(run=run)
            export_request.save()

            LOGGER.info(
                f"[tag:R365SGACUGA14][run:{run.id}][SEI:{source_entity_id}] Creating discovered entity."
            )
            discovered_entity = DiscoveredEntity(
                run=run,
                source_entity_id=source_entity_id,
                type=EntityType.GL_ACCOUNT.ident,
                export_request=export_request,
            )
            discovered_entity.attrs = self.r365_details[EntityType.GL_ACCOUNT.ident]
            discovered_entity.save()

            if create_or_update:
                LOGGER.info(
                    f"[tag:R365SGACUGA16][run:{run.id}][SEI:{source_entity_id}] "
                    f"Creating rest sub account."
                )
                json_response = self.piq_client.post_rest_sub_account(
                    r365_account_number, r365_account_name, piq_company_id
                )
            else:
                LOGGER.info(
                    f"[tag:R365SGACUGA18][run:{run.id}][SEI:{source_entity_id}] "
                    f"Updating rest sub account."
                )
                patch_id = next(
                    (
                        gl_account["id"]
                        for gl_account in piq_gl_accounts
                        if gl_account["account_number"] == r365_account_number
                    ),
                    None,
                )
                json_response = self.piq_client.patch_rest_sub_account(
                    patch_id=patch_id,
                    account_name=r365_account_name,
                    company=piq_company_id,
                )
            LOGGER.info(
                f"[tag:R365SGACUGA20][run:{run.id}][SEI:{source_entity_id}][ER:{export_request.id}]"
                f" Updating export_request."
            )
            export_request.http_request_url = json_response.url
            export_request.http_request_method = json_response.request.method
            export_request.http_request_json = json.loads(
                json_response.request.body.decode("utf8")
            )
            export_request.http_response_code = json_response.status_code
            export_request.http_response_body = json_response.text
            export_request.save()
            LOGGER.info(
                f"[tag:R365SGACUGA30][run:{run.id}][SEI:{source_entity_id}][DE:{discovered_entity.id}] "
                f"Updating discovered_entity."
            )
            discovered_entity.export_request = export_request
            discovered_entity.save()
            discovered_entities.append(discovered_entity)
        return discovered_entities

    def _update_sync_records(self, run: Run) -> List[DiscoveredEntity]:
        LOGGER.info(f"[tag:R365USR10][run:{run.id}] Import Entities process begins")
        discovered_entities = []

        if EntityType.GL_ACCOUNT.ident in self.entities_to_import:
            discovered_entities += self._sync_gl_accounts(run)

        if EntityType.VENDOR.ident in self.entities_to_import:
            discovered_entities += self._sync_vendors(run)

        if EntityType.BANK_ACCOUNT.ident in self.entities_to_import:
            discovered_entities += self._sync_bank_accounts(run)

        LOGGER.info(f"[tag:R365USR10][run:{run.id}] Import Entities process finished")
        return discovered_entities

    def start_sync_flow(self, run) -> List[DiscoveredEntity]:
        self._r365_login()
        self._fetch_r365_details()
        self._fetch_piq_details()

        sync_runs = []
        sync_runs += self._update_sync_records(run)

        return sync_runs


class PaymentInformationImportInterface(abc.ABC):
    def __init__(self, run: Run):
        self.run = run
        self.download_location = f"{TEMP_DOWNLOAD_DIR}/runs/{self.run.id}"

    @abc.abstractmethod
    def start_payment_import_flow(self, run: Run):
        pass


# pylint: disable=no-member
class R365PaymentsRunner(PaymentInformationImportInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.r365_client = R365CoreClient(self.run.job.login_url)
        self.r365_details = {"locations": {}, "vendors": {}, "payment_txns": []}

    def _login(self):
        self.r365_details["session_id"] = self.r365_client.get_auth_credentials(
            self.run.job.username, self.run.job.password
        )
        self.r365_details["user_id"] = self.r365_client.get_session_data(
            self.r365_details["session_id"]
        )

    def get_all_payment_txns(self):
        filters = "(substringof('AP+Payment'%2CTransactionType)+%25and%25+substringof('Approved'%2CApprovalStatus))"
        first_txn = self.r365_client.get_grid_source_request(
            grid_name="All+Transactions",
            count=1,
            is_employee="0",
            user_id=self.r365_details["user_id"],
            filters=filters,
        )
        all_txns = self.r365_client.get_grid_source_request(
            grid_name="All+Transactions",
            is_employee="0",
            user_id=self.r365_details["user_id"],
            filters=filters,
            count=first_txn[0]["__count"],
        )
        parsed_txns = []
        for txn in all_txns:
            parsed_txn = {
                "id": txn.get("Id"),
                "approval_status": txn.get("ApprovalStatus"),
                "location_name": txn.get("Location"),
                "payment_name": txn.get("Name"),
                "payment_number": txn.get("Number"),
                "payment_date": txn.get("Date"),
                "vendor_name": txn.get("Company"),
                "vendor_paid_to": txn.get("PaidTo"),
                "payment_amt": txn.get("Amount"),
                "payment_amt_remaining": txn.get("AmountRemaining"),
                "bank_account": txn.get("CheckingAccount"),
                "txn_type": txn.get("TransactionType"),
                "txn_id": txn.get("TransactionId"),
                "posting_date": txn.get("PostingDate"),
                "payment_txn_id": txn.get("PaymentTransactionId"),
                "payment_txn_status": txn.get("PaymentTransactionStatus"),
                "accrual_start_date": txn.get("AccrualStartDate"),
                "accrual_end_date": txn.get("AccrualEndDate"),
                "has_vendor_payment_hold": txn.get("VendorHasPaymentHold"),
                "has_reversal_txn": txn.get("HasReversalTransaction"),
            }
            parsed_txns.append(parsed_txn)
        self.r365_details["payment_txns"] = parsed_txns

    def get_all_locations(self):
        all_locations = self.r365_client.get_locations_all()
        for location in all_locations:
            self.r365_details["locations"][
                location["dm_name"].split("-")[-1].strip()
            ] = location["Id"]

    def get_vendor_id(self, vendor_name: str, location_id: str):
        if self.r365_details["vendors"].get(vendor_name):
            return self.r365_details["vendors"].get(vendor_name)

        hacked_vendor_name = vendor_name
        if "'" in vendor_name:
            hacked_vendor_name = vendor_name.split("'")[0]

        filter_text = self.r365_client.prepare_filter_text(hacked_vendor_name)
        filters = f"substringof('{filter_text}'%2Ctolower(name))"
        vendors = self.r365_client.get_grid_source_vendor_cc(
            grid_name="Vendors",
            user_id=self.r365_details["user_id"],
            vendor_id="",
            filters=filters,
            location_ids=[location_id],
            transaction_type="3",
        )
        for vendor in vendors:
            vendor_id = (
                vendor["companyId"] if vendor["companyId"] else vendor["vendorId"]
            )
            self.r365_details["vendors"][vendor["name"]] = vendor_id

        return self.r365_details["vendors"].get(vendor_name)

    def get_invoices(self):
        for txn in self.r365_details["payment_txns"]:
            location_id = (
                self.r365_details["locations"].get(txn["location_name"])
                if txn.get("location_name") in self.r365_details["locations"]
                else None
            )
            txn_id = txn["txn_id"]
            vendor = txn["vendor_name"]
            vendor_id = self.get_vendor_id(vendor_name=vendor, location_id=location_id)
            apply_records = self.r365_client.get_transaction_apply_records(
                company=vendor_id,
                location=location_id,
                transaction_id=txn_id,
                trx_type="3",
            )
            invoices = []
            for apply_record in apply_records["applyRecords"]:
                if apply_record["apply"] == "0":
                    continue
                invoice = {
                    "location_id": apply_record.get("LocationId"),
                    "org_txn_total": apply_record.get("originalTransactionTotal"),
                    "org_disc_amt": apply_record.get("originalDiscountAmount"),
                    "org_apply_amt": apply_record.get("originalApplyAmount"),
                    "org_amt_remaining": apply_record.get("originalAmountRemaining"),
                    "invoice_id": apply_record.get("invoiceId"),
                    "invoice_number": apply_record.get("number"),
                    "invoice_date": apply_record.get("date"),
                    "txn_type": apply_record.get("transactionType"),
                    "txn_total": apply_record.get("transactionTotal"),
                    "disc_amt": apply_record.get("discountAmount"),
                    "check_run": apply_record.get("checkRun"),
                    "apply": apply_record.get("apply"),
                    "txn_apply_id": apply_record.get("transactionApplyId"),
                    "apply_date": apply_record.get("applyDate"),
                    "apply_amt": apply_record.get("applyAmount"),
                    "amt_remaining": apply_record.get("amountRemaining"),
                    "version": apply_record.get("version"),
                }
                invoices.append(invoice)
            txn["invoices"] = invoices

    def create_discovered_file(self, run: Run):
        reference_code = uuid.uuid1()
        discovered_file = DiscoveredFile.build_unique(
            run,
            reference_code,
            document_type=DocumentType.INVOICE.ident,
            file_format=FileFormat.JSON.ident,
            original_download_url="",
            original_filename=f"{reference_code}.json",
            document_properties={},
        )

        file_path = os.path.join(
            self.download_location, discovered_file.original_filename
        )
        Path(
            self.download_location,
        ).mkdir(parents=True, exist_ok=True)
        with open(file_path, "w") as invoice_file:
            json.dump(self.r365_details["payment_txns"], invoice_file)

        downloader = download.NoOpDownloader(
            local_filepath=f"{self.download_location}/{discovered_file.original_filename}",
        )
        download_discovered_file(discovered_file, downloader=downloader)

    def start_payment_import_flow(self, run: Run):
        self._login()
        self.get_all_payment_txns()
        self.get_all_locations()
        self.get_invoices()
        self.create_discovered_file(run=run)
