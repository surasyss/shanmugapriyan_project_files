import copy
import datetime
import logging
import math
from typing import List

from num2words import num2words
from spices.django3.coreobjects.models import BankAccount, Vendor, Location
from spices.enum_utils import BaseChoice
from spices.services import ContextualError

from apps.adapters.accounting.r365_core import R365CoreClient
from apps.adapters.base import AccountingPaymentUpdateInterface
from apps.error_codes import ErrorCode
from apps.jobconfig.models import PIQMapping
from apps.runs.models import Run, CheckRun, CheckRunExists, CheckRunDisabled
from integrator import settings

LOGGER = logging.getLogger("apps.adapters.accounting")

MISMATCH_TOLERANCE = 0.01


class CreditStatus(BaseChoice):
    UNUSED = ("unused", "Unused")
    USED = ("used", "Used")
    PARTIALLY_USED = ("partially_used", "PARTIALLY_USED")


class TxnType(BaseChoice):
    INVOICE = (1, "Invoice")
    CREDIT = (2, "Credit")
    PAYMENT = (3, "Payment")


class InvoiceNotApproved(Exception):
    pass


class R365CreditMemo:
    def __init__(self, r365_client: R365CoreClient):
        self.r365_client = r365_client
        self.user_id = None
        self.temp_transaction_id = "00000000-0000-0000-0000-000000000000"
        self.transaction_id = None
        self.location_id = None
        self.location_name = None
        self.vendor_id = None
        self.posting_date = None
        self.credit_txn = None
        self.fully_applied_invoices = {}

    @property
    def ctx(self):
        return self.r365_client.ctx

    # pylint: disable=no-member
    def search_credit_txn_id(self, piq_credit_number: str, piq_credit_amount: float):
        filters = (
            f"(substringof('{self.r365_client.prepare_filter_text(piq_credit_number)}'%2CNumber)+%25and%25+substringof('AP+Credit+Memo'"
            f"%2CTransactionType)+%25and%25+Amount+eq+{abs(piq_credit_amount)})"
        )

        credit_txns = self.r365_client.get_grid_source_request(
            grid_name="All+Transactions",
            user_id=self.user_id,
            order_by="ApprovalStatus+desc%2CDate+desc",
            count=250,
            filters=filters,
            is_employee="0",
            login_type="1",
        )
        credit_txn = [txn for txn in credit_txns if txn["Number"] == piq_credit_number]

        if len(credit_txn) != 1:
            LOGGER.warning(
                f"[tag:WER365CSC70]{self.ctx} Credit Transaction not found: ({piq_credit_number}) in r365"
            )
            raise ContextualError(
                code=ErrorCode.PE_INVOICE_NOT_FOUND.ident,
                message=ErrorCode.PE_INVOICE_NOT_FOUND.message.format(
                    invoice_numbers=piq_credit_number
                ),
                params={},
            )

        LOGGER.info(
            f"[tag:WER365CSC80]{self.ctx} Found credit invoice: {piq_credit_number}"
        )
        self.credit_txn = credit_txn[0]
        self.transaction_id = self.credit_txn["TransactionId"]
        self.posting_date = self.credit_txn["PostingDate"]

    def get_credit_txn(self):
        credit_txn = self.r365_client.get_transaction(
            transaction_id=self.transaction_id
        )
        self.location_id = credit_txn["locationId"]
        self.location_name = credit_txn["location"]
        self.vendor_id = credit_txn["companyId"]

        return credit_txn

    def get_credit_txn_details(self):
        return self.r365_client.get_transaction_details(
            transaction_id=self.transaction_id
        )

    def update_apply_records(self, records: dict, credit: dict, invoices: list) -> dict:
        """
        Updates the records as required
        :param records: List of invoice records received from GetTransactionApplyRecords API
        :param invoices: List of PIQ invoices which are part of checkrun
        :param credit: Credit
        :return: List of updated records
        """
        records_copy = copy.deepcopy(records)
        records_copy["applyRecords"] = sorted(
            records_copy["applyRecords"],
            key=lambda r: float(r["amountRemaining"]),
            reverse=True,
        )
        abs_credit_remaining = abs(float(credit["invoice_amount"]))

        for record in records_copy["applyRecords"]:
            record["date"] = datetime.datetime.strptime(
                record["date"], "%m/%d/%Y %I:%M:%S %p"
            ).strftime("%Y-%m-%dT%H:%M:00.000Z")
            record["applyDate"] = datetime.datetime.strptime(
                record["applyDate"], "%m/%d/%Y %I:%M:%S %p"
            ).strftime("%Y-%m-%dT%H:%M:00.000Z")
            record["transactionTotal"] = float(record["transactionTotal"])
            record["discountAmount"] = float(record["discountAmount"])
            record["applyAmount"] = float(record["applyAmount"])
            record["amountRemaining"] = float(record["amountRemaining"])
            record["isAlreadyApplied"] = False
            record["firstAppliedAmount"] = "0.00000"

            if abs_credit_remaining <= 0.0:
                break

            is_invoice_present = next(
                (
                    inv
                    for inv in invoices
                    if (
                        record["number"] == inv["invoice_number"]
                        and record["location"] == self.location_name
                    )
                ),
                None,
            )

            if is_invoice_present and record["amountRemaining"] > 0.0:
                invoice_remaining_amount = record["amountRemaining"]
                if abs_credit_remaining <= invoice_remaining_amount:
                    record["applyAmount"] = abs_credit_remaining
                    record["amountRemaining"] = round(
                        invoice_remaining_amount - abs_credit_remaining, 2
                    )

                if abs_credit_remaining > invoice_remaining_amount:
                    record["applyAmount"] = invoice_remaining_amount
                    record["amountRemaining"] = 0.0
                    self.fully_applied_invoices[record["number"]] = {
                        "Amount": record["transactionTotal"]
                    }

                record["apply"] = "1"
                record["applyDateStr"] = self.posting_date.split(" ")[0]
                record["originalApplyAmount"] = float(record["originalApplyAmount"])

                abs_credit_remaining = round(
                    abs_credit_remaining - invoice_remaining_amount, 2
                )
        return records_copy

    def get_txn_apply_records(self, credit: dict, invoices: list):
        apply_records = self.r365_client.get_transaction_apply_records(
            company=self.vendor_id,
            transaction_id=self.transaction_id,
            trx_type=TxnType.CREDIT.ident,
            location=self.location_id,
        )
        updated_apply_records = self.update_apply_records(
            apply_records, credit, invoices
        )

        return updated_apply_records["applyRecords"]

    @staticmethod
    def get_transaction(txn: dict):
        """
        Prepare & Returns Transaction Details
        :param txn: R365 - GetTransaction API response
        :return:
        """
        transaction = {
            "number": txn["number"],
            "companyId": txn["companyId"],
            "date": txn["date"].split(" ")[0],
            "docDate": txn["docDate"],
            "amount": txn["amount"],
            "franchising": txn["franchising"],
            "TaxFormType": txn["TaxFormType"],
            "_1099Box": txn["_1099Box"],
            "_1099Amount": txn["_1099Amount"],
            "locationId": txn["locationId"],
            "entryByItem": txn["entryByItem"],
            "unassignedAmountValue": txn["unassignedAmount"],
            "unassignedAmountLabel": "Unassigned Amount",
            "checkRun": txn["checkRun"],
            "approvalStatus": txn["approvalStatus"],
            "beginningBalance": txn["beginningBalance"],
            "transactionType": txn["transactionType"],
            "template": txn["template"],
            "accountingSystemId": txn["accountingSystemId"],
            "autoRecurrence": txn["autoRecurrence"],
            "daysInAdvance": int(txn["daysInAdvance"]),
            "templateTransactionId": txn["templateTransactionId"],
            "address1": txn["address1"],
            "address2": txn["address2"],
            "city": txn["city"],
            "state": txn["state"],
            "zip": txn["zip"],
            "transactionId": txn["transactionId"],
        }

        return transaction

    @staticmethod
    def get_transaction_details(txn_details: dict):
        """
        Returns the transaction details
        :param txn_details: R365 - GetTransactionDetails API response
        :return:
        """
        transaction_details = copy.deepcopy(txn_details)

        for txn in transaction_details:
            txn["avgSales"] = None
            txn["statisticalTransactionDetailId"] = None

        return transaction_details

    def credit_status(self):
        # if float(self.credit_txn['AmountRemaining']) == float(self.credit_txn['Amount']):
        if math.isclose(
            float(self.credit_txn["AmountRemaining"]),
            float(self.credit_txn["Amount"]),
            abs_tol=MISMATCH_TOLERANCE,
        ):
            return CreditStatus.UNUSED.ident
        elif math.isclose(
            float(self.credit_txn["AmountRemaining"]), 0, abs_tol=MISMATCH_TOLERANCE
        ):
            return CreditStatus.USED.ident
        else:
            return CreditStatus.PARTIALLY_USED.ident

    def save(self, credit: dict, invoices: list):
        self.search_credit_txn_id(credit["invoice_number"], credit["invoice_amount"])

        credit_status = self.credit_status()
        if credit_status == CreditStatus.USED.ident:
            LOGGER.info(
                f"[tag:WER36CMS80]{self.ctx} Skip applying credit since {credit} is already used."
            )

        if credit_status == CreditStatus.PARTIALLY_USED.ident:
            LOGGER.info(
                f"[tag:WER36CMS81]{self.ctx} Partially used credit workflow is not implemented."
            )

        if credit_status == CreditStatus.UNUSED.ident:
            LOGGER.info(
                f"[tag:WER36CMS82]{self.ctx} Credit {credit} unused. Applying credit"
            )
            txn = self.get_transaction(self.get_credit_txn())
            txn_details = self.get_transaction_details(self.get_credit_txn_details())
            apply_records = self.get_txn_apply_records(credit, invoices)
            self.r365_client.save_transaction(
                user_id=self.user_id,
                transaction=txn,
                transaction_details=txn_details,
                apply_records=apply_records,
                action="Save",
            )


class R365Invoice:
    def __init__(self, r365_client):
        self.r365_client = r365_client

    @property
    def ctx(self):
        return self.r365_client.ctx

    def get_unapproved_txns(self, user_id: str, location_name: str, vendor_name: str):
        location_name = self.r365_client.prepare_filter_text(location_name)
        vendor_name = self.r365_client.prepare_filter_text(vendor_name)

        text = f"%24inlinecount=allpages&%24format=json&gridName=All+Transactions&userID={user_id}&%24top=250&%24orderby=ApprovalStatus+desc%2CDate+desc&%24filter=(substringof('AP+Invoice'%2CTransactionType)+%25and%25+substringof('Unapproved'%2CApprovalStatus)+%25and%25+substringof('{vendor_name}'%2CCompany)+%25and%25+substringof('{location_name}'%2CLocation))"
        unapproved_txns = self.r365_client.get_grid_source_request_v1(text=text)
        return unapproved_txns

    def get_txn(self, txn_id: str) -> {}:
        txn = self.r365_client.get_transaction(transaction_id=txn_id)
        return txn

    @staticmethod
    def txn_adapter(txn: dict) -> {}:
        return {
            "number": txn.get("number"),
            "companyId": txn.get("companyId"),
            "companyText": txn.get("companyText"),
            "date": txn.get("date"),
            "docDate": txn.get("docDate"),
            "amount": txn.get("amount"),
            "paymentTermsId": txn.get("paymentTermsId"),
            "dueDate": txn.get("dueDate"),
            "TaxFormType": txn.get("TaxFormType"),
            "_1099Box": txn.get("_1099Box"),
            "_1099Amount": txn.get("_1099Amount"),
            "locationId": txn.get("locationId"),
            "creditExpected": txn.get("creditExpected"),
            "creditComment": txn.get("creditComment"),
            "franchising": txn.get("franchising"),
            "shortPay": txn.get("shortPay"),
            "unassignedAmountValue": txn.get("unassignedAmountValue"),
            "unassignedAmountLabel": txn.get("unassignedAmountLabel"),
            "entryByItem": txn.get("entryByItem"),
            "approvalStatus": txn.get("approvalStatus"),
            "assignVendorItemTab": txn.get("assignVendorItemTab"),
            "checkRun": txn.get("checkRun"),
            "beginningBalance": txn.get("beginningBalance"),
            "transactionType": txn.get("transactionType"),
            "template": txn.get("template"),
            "accountingSystemId": txn.get("accountingSystemId"),
            "autoRecurrence": txn.get("autoRecurrence"),
            "daysInAdvance": txn.get("daysInAdvance"),
            "templateTransactionId": txn.get("templateTransactionId"),
            "autoCreatePayment": txn.get("autoCreatePayment"),
            "paymentDate": txn.get("paymentDate"),
            "workflowStatus": txn.get("workflowStatus"),
            "RelatedToAsset": txn.get("RelatedToAsset"),
            "accrualStartDate": txn.get("accrualStartDate"),
            "accrualEndDate": txn.get("accrualEndDate"),
            "address1": txn.get("address1"),
            "address2": txn.get("address2"),
            "city": txn.get("city"),
            "state": txn.get("state"),
            "zip": txn.get("zip"),
            "isOnPaymentHold": txn.get("isOnPaymentHold"),
            "priority": txn.get("priority"),
            "countComplete": txn.get("countComplete"),
            "transactionId": txn.get("transactionId"),
        }

    def get_txn_details(self, txn_id: str) -> {}:
        txn_details = self.r365_client.get_transaction_details(transaction_id=txn_id)
        return txn_details

    def get_apply_records(self, location_id: str, vendor_id: str, txn_id: str):
        apply_records = self.r365_client.get_transaction_apply_records(
            company=vendor_id,
            transaction_id=txn_id,
            trx_type=TxnType.INVOICE.ident,
            location=location_id,
        )
        return apply_records

    def save(self, user_id: str, location_id: str, vendor_id: str, txn_id: str):
        transaction = self.txn_adapter(self.get_txn(txn_id))
        transaction_details = self.get_txn_details(txn_id)
        apply_records = self.get_apply_records(location_id, vendor_id, txn_id)

        self.r365_client.save_transaction(
            user_id=user_id,
            transaction=transaction,
            transaction_details=transaction_details,
            apply_records=apply_records.get("applyRecords"),
            action="Save",
            attachmentFileParameters=None,
            isNew=False,
            PurchaseOrderId="",
            preWorkflowSave=True,
            templateId=0,
        )

    def approve(self, txn_id: str):
        self.r365_client.approve_txn(
            transactions=[{"id": txn_id}],
            transactionType=TxnType.INVOICE.ident,
            autoCreatePayment=False,
        )

    def get_unapproved_invoices(
        self, checkrun: dict, user_id: str, location: dict, vendor: dict
    ) -> []:
        location_name = location[1]
        vendor_name = vendor[1]

        unapproved_txns = self.get_unapproved_txns(
            user_id=user_id, location_name=location_name, vendor_name=vendor_name
        )
        unapproved_invoices = []
        unapproved_invoice_numbers = []
        for invoice in checkrun.get("invoices"):
            unapproved_invoice = [
                txn
                for txn in unapproved_txns
                if txn.get("Number") == invoice.get("invoice_number")
            ]
            if unapproved_invoice:
                unapproved_invoice_numbers.append(unapproved_invoice[0].get("Number"))
                unapproved_invoices.extend(unapproved_invoice)

        return unapproved_invoices, unapproved_invoice_numbers

    def approve_invoices(
        self, user_id: str, unapproved_invoices: [], location: tuple, vendor: tuple
    ):
        location_id = location[0]
        vendor_id = vendor[0]

        for unapproved_invoice in unapproved_invoices:
            txn_id = unapproved_invoice.get("TransactionId")
            self.save(
                user_id=user_id,
                location_id=location_id,
                vendor_id=vendor_id,
                txn_id=txn_id,
            )
            self.approve(txn_id=txn_id)


class R365ManualPayment:
    def __init__(self, r365_client: R365CoreClient, run: Run, user_id: str = None):
        self.r365_client = r365_client
        self.user_id = user_id
        self.run = run
        self.strict_location_check = (
            self.run.job.custom_properties.get("strict_location_check", True)
            if self.run.job.custom_properties
            else True
        )
        self.strict_bank_acc_check = (
            self.run.job.custom_properties.get("strict_bank_acc_check", True)
            if self.run.job.custom_properties
            else True
        )
        self.use_payment_number_prefix = (
            self.run.job.custom_properties.get("use_payment_number_prefix", True)
            if self.run.job.custom_properties
            else True
        )
        self.temp_transaction_id = "00000000-0000-0000-0000-000000000000"
        self.credit_list = None
        self.fully_applied_invoices = {}

    @property
    def ctx(self):
        return self.r365_client.ctx

    # pylint: disable=no-member
    def search_location(self, gl_account_id: str, piq_location_id: str):
        """
        Searches Location
        :param gl_account_id:
        :param piq_location_id:
        :return:
        """
        locations = self.r365_client.get_locations(
            user_id=self.user_id,
            transaction_type=TxnType.PAYMENT.ident,
            gl_account_id=gl_account_id,
        )

        location = [
            (loc["locationId"], loc["label"])
            for loc in locations
            if loc["locationNumber"] == piq_location_id
        ]

        if len(location) != 1:
            LOGGER.warning(
                f"[tag:WER36MPSL70]{self.ctx} Location not found: ({piq_location_id}) in r365"
            )
            raise ContextualError(
                code=ErrorCode.PE_LOCATION_NOT_FOUND.ident,
                message=ErrorCode.PE_LOCATION_NOT_FOUND.message.format(
                    location_name=piq_location_id
                ),
                params={},
            )

        LOGGER.info(f"[tag:WER36MPSL80]{self.ctx} Found location by id: {location}")
        return location[0]

    def search_checking_bank_account(
        self, account_id: str, piq_bnk_acct: str, location: dict
    ):
        """
        Searches Checking Bank Account
        :param location:
        :param account_id:
        :param piq_bnk_acct:
        :return:
        """
        location_id = location[0]
        chk_bank_accts = self.r365_client.get_checking_bank_accounts(
            user_id=self.user_id,
            location=location_id,
            account_id=account_id,
            transaction_id=self.temp_transaction_id,
        )

        chk_bank_acct = [
            (acct["checkingAccountId"], acct["accountName"])
            for acct in chk_bank_accts
            if acct["accountName"].lower() == piq_bnk_acct.lower()
        ]

        if not chk_bank_acct and not self.strict_bank_acc_check:
            chk_bank_acct = [
                (acct["checkingAccountId"], acct["accountName"])
                for acct in chk_bank_accts
                if acct["accountName"].lower() in piq_bnk_acct.lower()
                or piq_bnk_acct.lower() in acct["accountName"].lower()
            ]

        if len(chk_bank_acct) != 1:
            LOGGER.warning(
                f"[tag:WER36MPSCBA70]{self.ctx} Checking Bank Account not found: ({piq_bnk_acct}) in r365"
            )
            raise ContextualError(
                code=ErrorCode.PE_BANK_ACC_NOT_FOUND.ident,
                message=ErrorCode.PE_BANK_ACC_NOT_FOUND.message.format(
                    bank_account=piq_bnk_acct
                ),
                params={},
            )

        LOGGER.info(
            f"[tag:WER36MPSCBA80]{self.ctx} Found Checking Bank Account: {chk_bank_acct}"
        )
        return chk_bank_acct[0]

    def search_vendor(self, piq_vendor_id: str, location: dict):
        """
        Searches Vendor
        :param location:
        :param piq_vendor_id:
        :return:
        """
        location_id = location[0]
        # This is to handle a bug in R365. Vendor search doesn't work for "'" & ")"
        hacked_vendor_id = piq_vendor_id
        if "'" in piq_vendor_id:
            hacked_vendor_id = piq_vendor_id.split("'")[0]

        if ")" in piq_vendor_id:
            hacked_vendor_id = hacked_vendor_id.split(")")[0]

        filter_text = self.prepare_filter_text_for_vendor_name(hacked_vendor_id)

        grid_name = "Vendors"
        filters = f"substringof('{filter_text}'%2Ctolower(label))"

        vendors = self.r365_client.get_grid_source_vendor_cc(
            user_id=self.user_id,
            grid_name=grid_name,
            filters=filters,
            location_ids=[location_id],
            vendor_id="",
            transaction_type="",
        )
        vendor = []
        for ven in vendors:
            piq_vendor_id_lower = piq_vendor_id.lower().strip()
            if any(
                (piq_vendor_id_lower == ven.get(key, "").lower().strip())
                for key in ["name", "NameOnly", "number"]
            ):
                vendor_address = {
                    "address1": ven["address1"],
                    "address2": ven["address2"],
                    "city": ven["city"],
                    "state": ven["state"],
                    "country": ven["country"],
                    "zip_code": ven["zipCode"],
                }
                vendor = [(ven["vendorId"], ven["name"], vendor_address)]

        if not vendor:
            LOGGER.warning(
                f"[tag:WER36MPSV65]{self.ctx} Vendor not found: ({piq_vendor_id}) in r365"
            )
            raise ContextualError(
                code=ErrorCode.PE_VENDOR_NOT_FOUND.ident,
                message=ErrorCode.PE_VENDOR_NOT_FOUND.message.format(
                    vendor_name=piq_vendor_id
                ),
                params={},
            )

        if len(vendor) > 1:
            LOGGER.warning(
                f"[tag:WER36MPSV70]{self.ctx} Multiple vendors found: ({piq_vendor_id}) in r365"
            )
            raise ContextualError(
                code=ErrorCode.PE_VENDOR_SELECTION_FAILED.ident,
                message=ErrorCode.PE_VENDOR_SELECTION_FAILED.message.format(
                    vendor_name=piq_vendor_id
                ),
                params={},
            )

        LOGGER.info(f"[tag:WER36MPSV80]{self.ctx} Found vendor by id: {vendor}")
        return vendor[0]

    @staticmethod
    def get_amount_in_text(amount: float) -> str:
        """
        Convert float amount in text (R365 specific)
        :param amount:
        :return: Amount in text
        """
        dollar_amount, cent_amount = divmod(amount, 1)
        dollar_amount = (
            num2words(dollar_amount)
            .replace(",", "")
            .replace(" and ", " ")
            .replace("-", " ")
        )
        amount_in_text = f"{dollar_amount} and {int(cent_amount * 100)}/100"
        return amount_in_text

    def get_transaction(
        self,
        check_run: dict,
        location: tuple,
        vendor: tuple,
        checking_bank_account: tuple,
    ):
        """
        Prepare & Returns Transaction Details
        :param vendor:
        :param checking_bank_account:
        :param location:
        :param check_run:
        :return:
        """
        location_id = location[0]
        vendor_id = vendor[0]
        vendor_address = vendor[2]
        checking_bank_account_id = checking_bank_account[0]
        if self.use_payment_number_prefix:
            payment_number = f'PIQ_{check_run["payment_number"]}'
        else:
            payment_number = str(check_run["payment_number"])
        transaction = {
            "number": payment_number,
            "companyId": vendor_id,
            "checkingAccountId": checking_bank_account_id,
            "date": f'{check_run["payment_date"]}',
            "comment": "Created with PlateIQ!",
            "amount": f'{check_run["payment_total"]}',
            "amountText": self.get_amount_in_text(check_run["payment_total"]),
            "locationId": location_id,
            "address1": vendor_address["address1"],
            "address2": vendor_address["address2"],
            "city": vendor_address["city"],
            "state": vendor_address["state"],
            "zip": vendor_address["zip_code"],
            "country": vendor_address["country"],
            "checkRun": "",
            "approvalStatus": "1",
            "beginningBalance": "0",
            "transactionType": TxnType.PAYMENT.ident,
            "template": "0",
            "accountingSystemId": None,
            "autoRecurrence": "",
            "daysInAdvance": "",
            "templateTransactionId": None,
            "transactionId": self.temp_transaction_id,
        }
        return transaction

    def update_apply_records(
        self,
        records: dict,
        invoices: list,
        total: float,
        location: tuple,
        payment_date: str,
    ) -> dict:
        """
        Updates the records as required
        :param payment_date:
        :param location:
        :param records: List of invoice records received from GetTransactionApplyRecords API
        :param invoices: List of PIQ invoices which are part of checkrun
        :param total: Total Checkrun amount
        :return: List of updated records
        """
        location_name = location[1]
        records_copy = copy.deepcopy(records)
        for record in records_copy["applyRecords"]:
            record["date"] = datetime.datetime.strptime(
                record["date"], "%m/%d/%Y %I:%M:%S %p"
            ).strftime("%Y-%m-%dT%H:%M:00.000Z")
            record["applyDate"] = datetime.datetime.strptime(
                record["applyDate"], "%m/%d/%Y %I:%M:%S %p"
            ).strftime("%Y-%m-%dT%H:%M:00.000Z")
            record["transactionTotal"] = float(record["transactionTotal"])
            record["discountAmount"] = float(record["discountAmount"])
            record["applyAmount"] = float(record["applyAmount"])
            record["amountRemaining"] = float(record["amountRemaining"])
            record["isAlreadyApplied"] = False
            record["firstAppliedAmount"] = "0.00000"

            if float(record["originalApplyAmount"]) != 0.0:
                record["firstAppliedAmount"] = record["originalApplyAmount"]

            if self.strict_location_check:
                is_invoice_present = [
                    inv
                    for inv in invoices
                    if (
                        record["number"] == inv["invoice_number"]
                        and record["location"] == location_name
                    )
                ]
            else:
                is_invoice_present = [
                    inv for inv in invoices if record["number"] == inv["invoice_number"]
                ]

            if is_invoice_present:
                record["apply"] = 1
                record["applyDateStr"] = payment_date

                if total >= record["amountRemaining"]:
                    total -= record["amountRemaining"]
                    record["applyAmount"] = round(record["amountRemaining"], 2)
                    record["amountRemaining"] = 0.0
                else:
                    record["applyAmount"] = round(total, 2)
                    record["amountRemaining"] = round(
                        record["amountRemaining"] - record["applyAmount"], 2
                    )
                    total = 0.0

        return records_copy

    def prepare_filter_text_for_vendor_name(self, vendor_name: str):
        # Adding this to handle special case in vendor name
        # Problem statement: R365 doesn't give proper results if vendor_name contains single quote
        # As of now we have seen single quote in vendor name hence adding check for the same.
        vendor_name = self.r365_client.prepare_filter_text(vendor_name)
        if "%27" in vendor_name:
            vendor_name = vendor_name.replace("%27", "''")

        if "%28" in vendor_name:
            vendor_name = vendor_name.replace("%28", "(")

        return vendor_name

    def get_txn_by_number(
        self, user_id: str, location_name: str, vendor_name: str, number: str
    ):
        location_name = self.r365_client.prepare_filter_text(location_name)
        vendor_name = self.prepare_filter_text_for_vendor_name(vendor_name)

        text = f"%24inlinecount=allpages&%24format=json&gridName=All+Transactions&userID={user_id}&%24top=250&%24orderby=ApprovalStatus+desc%2CDate+desc&%24filter=(substringof('AP+Invoice'%2CTransactionType)+%25and%25+substringof('{number}'%2CNumber)+%25and%25+substringof('{vendor_name}'%2CCompany)+%25and%25+substringof('{location_name}'%2CLocation))"
        txns = self.r365_client.get_grid_source_request_v1(text=text)
        return txns

    def get_filtered_apply_records(
        self, check_run: dict, location: tuple, vendor: tuple, payment_date: str
    ):
        location_id = location[0]
        location_name = location[1]
        vendor_id = vendor[0]
        vendor_name = vendor[1]

        invoice_list = [
            inv for inv in check_run["invoices"] if inv["invoice_amount"] >= 0.0
        ]
        apply_records = self.r365_client.get_transaction_apply_records(
            company=vendor_id,
            transaction_id=self.temp_transaction_id,
            trx_type=TxnType.PAYMENT.ident,
            location=location_id,
        )

        updated_apply_records = self.update_apply_records(
            apply_records,
            invoice_list,
            check_run["payment_total"],
            location=location,
            payment_date=payment_date,
        )

        missing_invoices = []
        full_credit_applied_invoices = []
        for inv in invoice_list:
            if self.strict_location_check:
                missing_invoice = (
                    inv["invoice_number"]
                    if (inv["invoice_number"], location_name)
                    not in [
                        (r["number"], r["location"])
                        for r in updated_apply_records["applyRecords"]
                    ]
                    else None
                )
            else:
                missing_invoice = (
                    inv["invoice_number"]
                    if (inv["invoice_number"])
                    not in [
                        (r["number"]) for r in updated_apply_records["applyRecords"]
                    ]
                    else None
                )
            if missing_invoice:
                # TODO The get_txn_by_number query is broken and does not return any txns for invoices that are in R365
                # Consider removing the logic as we should be allowing CR missing invoices in the R365 apply list
                # only if we fully applied a credit from the CR to them in R365APIRunner._update_payment_record

                invoice_txn = self.get_txn_by_number(
                    user_id=self.user_id,
                    location_name=location_name,
                    vendor_name=vendor_name,
                    number=inv["invoice_number"],
                )
                # Checking if the invoice remaining amount is 0.0 since R365 doesn't list such invoices
                # in the apply records query. We will export the payment excluding such invoices
                if len(invoice_txn) == 1:
                    if math.isclose(
                        float(invoice_txn[0].get("AmountRemaining")),
                        float(0.0),
                        abs_tol=MISMATCH_TOLERANCE,
                    ):
                        full_credit_applied_invoices.append(invoice_txn[0])
                elif inv["invoice_number"] in self.fully_applied_invoices.keys():
                    full_credit_applied_invoices.append(
                        self.fully_applied_invoices[inv["invoice_number"]]
                    )
                else:
                    missing_invoices.append(missing_invoice)

        if missing_invoices:
            missing_invoices_str = ", ".join(missing_invoices)
            LOGGER.warning(
                f"[tag:WER36MPGFAR70]{self.ctx} Invoice(s) not found: ({missing_invoices}) in r365"
            )
            raise ContextualError(
                code=ErrorCode.PE_INVOICE_NOT_FOUND.ident,
                message=ErrorCode.PE_INVOICE_NOT_FOUND.message.format(
                    invoice_numbers=missing_invoices_str
                ),
                params={},
            )

        return updated_apply_records["applyRecords"], full_credit_applied_invoices

    def validate_apply_records(
        self,
        apply_records: dict,
        check_run: dict,
        location: tuple,
        full_credit_applied_invoices: list,
    ):
        location_name = location[1]
        total = 0.0
        amount_remaining = 0.0
        applied_amount = 0.0
        if self.credit_list:
            total = sum(float(c["invoice_amount"]) for c in self.credit_list)

        # Doing this because if the invoice remaining amount is 0.0 then it doesn't list in apply records
        # Currently it doesn't care if multiple credits are applied to the same invoice
        # and the credits are part of different payments (its a bug, if such case exists)
        for inv in full_credit_applied_invoices:
            total += float(inv["Amount"])

        invoices = [
            inv["invoice_number"]
            for inv in check_run["invoices"]
            if inv["invoice_amount"] >= 0.0
        ]
        filtered_records = [r for r in apply_records if r["number"] in invoices]

        for record in filtered_records:
            if self.strict_location_check:
                piq_invoice = next(
                    (
                        inv
                        for inv in check_run["invoices"]
                        if (
                            inv["invoice_number"] == record["number"]
                            and record["location"] == location_name
                            and inv["invoice_amount"] > 0.0
                        )
                    ),
                    None,
                )
            else:
                piq_invoice = next(
                    (
                        inv
                        for inv in check_run["invoices"]
                        if inv["invoice_number"] == record["number"]
                        and inv["invoice_amount"] > 0.0
                    ),
                    None,
                )
            if not piq_invoice:
                continue

            total += float(record["transactionTotal"])
            amount_remaining += float(record["amountRemaining"])
            applied_amount += float(record["applyAmount"])

            # Commenting this since piq_invoice_date is sometimes different from R365 dates
            # record_date = datetime.datetime.strptime(record['date'], '%Y-%m-%dT%H:%M:%S.000Z').strftime('%-m/%-d/%Y')
            # if record_date != piq_invoice['invoice_date']:
            #     post_error_msg = f'invoice_date mis-match for {piq_invoice["invoice_number"]}.' \
            #                      f' Expected: {piq_invoice["invoice_date"]}, Actual: {record_date}'

            if not math.isclose(
                record["transactionTotal"],
                piq_invoice["invoice_amount"],
                abs_tol=MISMATCH_TOLERANCE,
            ):
                self.__raise_amount_mismatch(
                    expected=piq_invoice["invoice_amount"],
                    actual=record["transactionTotal"],
                    message=f"Invoice amounts mismatched for the invoice#: {piq_invoice['invoice_number']} in "
                    "Restaurant365. Invoice amount in payment is {expected} but its {actual} in Restaurant365",
                )

        chequerun_id = check_run["chequerun_id"]
        total = round(total, 2)
        if not math.isclose(
            total, check_run["payment_total"], abs_tol=MISMATCH_TOLERANCE
        ):
            self.__raise_amount_mismatch(
                expected=check_run["payment_total"],
                actual=total,
                message=f"Payment amount for {chequerun_id} does not match sum of invoice amounts in Restaurant365."
                " Payment amount is {expected}, but invoices total is {actual}.",
            )

        amount_remaining = round(amount_remaining, 2)
        if not math.isclose(amount_remaining, 0, abs_tol=MISMATCH_TOLERANCE):
            self.__raise_amount_mismatch(
                expected=0,
                actual=amount_remaining,
                message="Remaining amount for all invoices after applying payment should be zero, but is {actual}."
                " This can happen if some credits were missed or not found. Please contact support.",
            )

        applied_amount = round(applied_amount, 2)
        if not math.isclose(
            applied_amount, check_run["payment_total"], abs_tol=MISMATCH_TOLERANCE
        ):
            self.__raise_amount_mismatch(
                expected=check_run["payment_total"],
                actual=applied_amount,
                message=f"Payment amount for {chequerun_id} does not match sum of applied amounts for invoices."
                " Payment amount is {expected}, but applied amount total is {actual}.",
            )

        return apply_records

    @staticmethod
    def __raise_amount_mismatch(expected: float, actual: float, message: str):
        expected_str = str(round(expected, 3))
        actual_str = str(round(actual, 3))
        final_message = message.format(expected=expected_str, actual=actual_str)
        raise ContextualError(
            code=ErrorCode.PE_VALIDATION_AMOUNT_MISMATCH.ident,  # pylint: disable=no-member
            message=final_message,
            params={
                "expected": expected,
                "actual": actual,
            },
        )

    def check_acct_dup_number(self, chk_number: str, checking_bank_account: tuple):
        checking_bank_account_id = checking_bank_account[0]
        response = self.r365_client.detect_checking_account_duplicate_number(
            user_id=self.user_id,
            transaction_id=self.temp_transaction_id,
            start_check_number=chk_number,
            checking_account_id=checking_bank_account_id,
        )
        return response

    def approve(
        self,
        check_run: dict,
        location: tuple,
        vendor: tuple,
        checking_bank_account: tuple,
    ):
        transaction = self.get_transaction(
            check_run,
            location=location,
            vendor=vendor,
            checking_bank_account=checking_bank_account,
        )

        is_chk_number_exists = self.check_acct_dup_number(
            transaction["number"], checking_bank_account=checking_bank_account
        )

        if is_chk_number_exists:
            LOGGER.warning(
                f"[tag:WER36MPAPR10]{self.ctx} "
                f'Checking Account Payment Number already exists - {transaction["number"]}'
            )
            raise ContextualError(
                code=ErrorCode.PE_PAYMENT_CONFLICT.ident,
                message=ErrorCode.PE_PAYMENT_CONFLICT.message.format(
                    payment_number=transaction["number"]
                ),
                params={},
            )

        apply_records, full_credit_applied_invoices = self.get_filtered_apply_records(
            check_run=check_run,
            location=location,
            vendor=vendor,
            payment_date=check_run["payment_date"],
        )
        validated_apply_records = self.validate_apply_records(
            apply_records,
            check_run,
            location=location,
            full_credit_applied_invoices=full_credit_applied_invoices,
        )
        self.r365_client.save_transaction(
            user_id=self.user_id,
            transaction=transaction,
            transaction_details=[],
            apply_records=validated_apply_records,
            action="Approve",
        )

    # pylint: disable=no-member
    def search_location_by_location_id(self, piq_location_id: str):
        """
        Searches Location as per location id.
        :param piq_location_id:location id from r365
        :return:
        """
        filters = f"substringof('{piq_location_id}'%2CLocationNumber)"
        locations = self.r365_client.get_grid_source_request(
            grid_name="Locations",
            user_id=self.user_id,
            order_by="LocationName",
            count=25,
            filters=filters,
            is_employee="0",
            login_type="1",
        )

        # Adding this condition since there can be multiple search results
        locations = [l for l in locations if l["LocationNumber"] == piq_location_id]

        if not locations:
            LOGGER.warning(
                f"[tag:WER36MPSLBID70]{self.ctx} Location not found: ({piq_location_id}) in r365"
            )
            raise ContextualError(
                code=ErrorCode.PE_LOCATION_NOT_FOUND.ident,
                message=ErrorCode.PE_LOCATION_NOT_FOUND.message.format(
                    location_name=piq_location_id
                ),
                params={},
            )
        if len(locations) > 1:
            LOGGER.warning(
                f"[tag:WER36MPSLBID71]{self.ctx} Multiple locations found: ({piq_location_id}) in r365"
            )
            raise ContextualError(
                code=ErrorCode.PE_LOCATION_SELECTION_FAILED.ident,
                message=ErrorCode.PE_LOCATION_SELECTION_FAILED.message.format(
                    location_name=piq_location_id
                ),
                params={},
            )

        location = locations[0]
        LOGGER.info(
            f"[tag:WER36MPSLBID80]{self.ctx} While searching location by id found location by id : {location}"
        )
        return {
            "location_name": location["LocationName"],
            "location_id": location["LocationId"],
        }


class R365APIRunner(AccountingPaymentUpdateInterface):
    create_driver = False

    def __init__(self, run: Run):
        super().__init__(run)
        self.run = run
        self.user_id = None
        self.r365_client = R365CoreClient(run.job.login_url)
        self.manual_payment = R365ManualPayment(self.r365_client, run=run)
        self.credit_memo = R365CreditMemo(self.r365_client)
        self.invoice = R365Invoice(self.r365_client)

    def _login(self, run: Run):
        """Login to R365"""
        session_id = self.r365_client.get_auth_credentials(
            run.job.username, run.job.password
        )
        LOGGER.debug(f"Session ID: {session_id}")
        self.user_id = self.r365_client.get_session_data(session_id)
        self.manual_payment.user_id = self.user_id
        self.credit_memo.user_id = self.user_id
        LOGGER.info(f"User ID: {self.user_id}")

    def _check_payment_in_r365(
        self,
        checkrun_id: str,
        number: str,
        amount: float,
        location_id: str,
        vendor_id: str,
    ):
        """
        Checks if payment number exists in R365
        :param number: Check run Payment Number
        :param amount: Check run total
        :return: Payment txn id
        """
        # getting location name from r365 as per id
        location_data = self.manual_payment.search_location_by_location_id(
            piq_location_id=location_id
        )
        payments = []
        for prefix in ("", "PIQ_"):
            prefix_number = f"{prefix}{self.r365_client.prepare_filter_text(number)}"
            filters = (
                f'(substringof(\'{self.r365_client.prepare_filter_text(location_data["location_name"])}\''
                f"%2CLocation)+%25and%25"
                f"+substringof('{self.r365_client.prepare_filter_text(vendor_id)}'%2CCompany)+%25and%25"
                f"+substringof('{prefix_number}'%2CNumber)+%25and%25"
                f"+Amount+eq+{abs(amount)}+%25and%25"
                f"+substringof('AP+Payment'%2CTransactionType))"
            )

            txns = self.r365_client.get_grid_source_request(
                grid_name="All+Transactions",
                user_id=self.user_id,
                order_by="ApprovalStatus+desc%2CDate+desc",
                count=250,
                filters=filters,
                is_employee="0",
                login_type="1",
            )

            payments.extend(
                [
                    (txn["TransactionId"], txn["Number"])
                    for txn in txns
                    if txn["Number"] == prefix_number
                ]
            )

            if payments:
                LOGGER.warning(
                    f"[tag:WER36CP70][cr:{checkrun_id}][PN:{prefix_number}]"
                    f"[AMT:{amount}][LOC:{location_id}] Found Payment"
                )
                raise ContextualError(
                    code=ErrorCode.PE_DUPLICATE_TXN_FOUND.ident,  # pylint: disable=no-member
                    message=ErrorCode.PE_DUPLICATE_TXN_FOUND.message.format(  # pylint: disable=no-member
                        prefix_number=number, amount=amount
                    ),
                    params={},
                )

    def _update_payment_record(self, run: Run, check_run: dict):
        location = self.manual_payment.search_location(
            gl_account_id=None, piq_location_id=check_run["location_id"]
        )
        checking_bank_account = self.manual_payment.search_checking_bank_account(
            account_id=None, piq_bnk_acct=check_run["bank_account"], location=location
        )
        vendor = self.manual_payment.search_vendor(
            piq_vendor_id=check_run["vendor_id"], location=location
        )

        # Invoice approval workflow
        (
            unapproved_invoices,
            unapproved_invoice_numbers,
        ) = self.invoice.get_unapproved_invoices(
            checkrun=check_run, user_id=self.user_id, location=location, vendor=vendor
        )
        if unapproved_invoices:
            if run.job.custom_properties and run.job.custom_properties.get(
                "r365_auto_approve"
            ):
                try:
                    self.invoice.approve_invoices(
                        user_id=self.user_id,
                        unapproved_invoices=unapproved_invoices,
                        location=location,
                        vendor=vendor,
                    )
                except Exception as excep:
                    # raise InvoiceNotApproved(f'[tag:WER365UPR70] One of more invoices not approved. {excep}')
                    raise ContextualError(
                        code=ErrorCode.PE_INVOICE_NOT_APPROVED.ident,
                        message=ErrorCode.PE_INVOICE_NOT_APPROVED.message.format(
                            invoice_numbers=unapproved_invoice_numbers
                        ),
                        params={},
                    )
            else:
                raise ContextualError(
                    code=ErrorCode.PE_INVOICE_NOT_APPROVED.ident,
                    message=ErrorCode.PE_INVOICE_NOT_APPROVED.message.format(
                        invoice_numbers=unapproved_invoice_numbers
                    ),
                    params={},
                )

        invoices = [
            inv for inv in check_run["invoices"] if inv["invoice_amount"] >= 0.0
        ]
        self.manual_payment.credit_list = [
            inv for inv in check_run["invoices"] if inv["invoice_amount"] < 0.0
        ]

        for credit in self.manual_payment.credit_list:
            self.credit_memo.save(credit, invoices)

        # Save records of R365 invoices that have been fully paid by applying a CR credit to them.
        # This is required as once R365 invoices are fully applied, we can't query them during the payment export.
        self.manual_payment.fully_applied_invoices = (
            self.credit_memo.fully_applied_invoices
        )
        self.credit_memo.fully_applied_invoices = {}

        self.manual_payment.date = check_run["payment_date"]
        self.manual_payment.approve(
            check_run=check_run,
            location=location,
            vendor=vendor,
            checking_bank_account=checking_bank_account,
        )
        self.manual_payment.fully_applied_invoices = {}

    def _update_payment_records(self, run: Run) -> List[CheckRun]:
        LOGGER.info(f"[tag:WEAARAUPR10] Updating Payment Records for {self.run}")
        all_created_checkruns = []
        for chequerun_id, check_run_dict in self.run.request_parameters[
            "accounting"
        ].items():
            check_run_dict = _update_request_parameters(run, check_run_dict)
            LOGGER.info(
                f"[tag:WEAARAUPR20][server_cr:{chequerun_id}] "
                f"Updating payment record for Check Run ID: {check_run_dict}"
            )

            if (
                settings.IGNORE_RETRYING_FAILED_CHECKRUN
                and self._validate_preconditions_for_creating_check_run(
                    run, chequerun_id
                )
            ):
                LOGGER.info(
                    f"[tag:WEAARAUPR30][run:{run.id}][server_cr:{chequerun_id}] Check Run creation conditions "
                    f"are not met."
                )
                continue

            try:
                check_run = CheckRun.create_unique(self.run, chequerun_id)
            except CheckRunExists as exc:
                if not exc.previous_checkrun.is_patch_success:
                    # if it was successful, but the patch hasn't finished, add it to the list of checkruns for
                    # which we'll notify Core API of success
                    all_created_checkruns.append(exc.previous_checkrun)
                # do not proceed further for duplicates
                continue

            except CheckRunDisabled as exc:
                LOGGER.debug(f"[tag:RUPR][run:{run.id}] {str(exc)}")
                continue
            # Set context to add the checkrun to important log statement
            self.r365_client.set_context(checkrun_id=check_run.id)

            try:
                if check_run_dict["payment_total"] < 0:
                    raise ContextualError(
                        ErrorCode.PE_PAYMENT_AMOUNT_NEGATIVE.ident,  # pylint: disable=no-member
                        ErrorCode.PE_PAYMENT_AMOUNT_NEGATIVE.message,  # pylint: disable=no-member
                        params={"payment_total": check_run_dict["payment_total"]},
                    )
                self._check_payment_in_r365(
                    checkrun_id=check_run.id,
                    number=check_run_dict["payment_number"],
                    amount=check_run_dict["payment_total"],
                    location_id=check_run_dict["location_id"],
                    vendor_id=check_run_dict["vendor_id"],
                )
                self._update_payment_record(run=run, check_run=check_run_dict)
                check_run.record_export_success()
            except ContextualError as exc:
                check_run.record_export_failure(exc)
                settings.PIQ_CORE_CLIENT.post_billpay_cheque_error(
                    chequerun_id, exc.message
                )

            all_created_checkruns.append(check_run)
        return all_created_checkruns

    @staticmethod
    def _validate_preconditions_for_creating_check_run(
        run: Run, check_run_id: int
    ) -> bool:
        # skip creating CheckRuns for those payments which have already failed more than 10 times in the past
        return bool(
            CheckRun.objects.filter(run=run, check_run_id=check_run_id).count() > 10
        )

    def start_payment_update_flow(self, run: Run) -> List[CheckRun]:
        """
        Initiates the Payment Update Workflow
        :param run: Run Object
        :return: Returns the list of Check Runs
        """
        self._login(run)
        check_runs = self._update_payment_records(run)
        return check_runs

    def login_flow(self, run: Run) -> bool:
        self._login(run=run)


def _update_request_parameters(run: Run, check_run_dict: dict):
    """
    Updates the request parameters with the PIQ Mappings
    :param run:
    :param check_run_dict: Contains details of a particular checkrun
    :return:
    """
    fields = [
        ("location_id", Location),
        ("vendor_id", Vendor),
        ("bank_account", BankAccount),
    ]

    for (key, coreobject_cls) in fields:
        data = check_run_dict[key].lower()
        mapping = (
            PIQMapping.objects.filter(
                job=run.job,
                mapping_data=data,
                piq_data__type=coreobject_cls.__coreobjects_type__,
            )
            .values("mapped_to")
            .first()
        )

        if mapping:
            check_run_dict[key] = mapping["mapped_to"]

    return check_run_dict
