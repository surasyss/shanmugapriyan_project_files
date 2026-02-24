from typing import List

from selenium.webdriver.remote.webelement import WebElement
from spices.django3.issues.models import Issue
from spices.services import ContextualError

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import (
    get_url,
    explicit_wait_till_visibility,
)
from apps.error_codes import ErrorCode
from apps.runs.models import Run, DiscoveredFile, VendorPayment, PaymentStatus

# Payments Page Locators
PAYMENT_PAGE_LOCATORS = {
    "SELECT_ACCOUNT_TAB": 'select[id="SelectAccount"]',
    "INVOICES_LOC": 'a[id="nav-invoice"]',
    "PAYMENT_BUTTON": '//button[contains(text(),"Pay")]',
    "PAYMENTS_TAB": 'div[id="payment-tabs"]',
    "CARD_TAB": 'a[href="#card"]',
    "CARD_DATA_FORM": "form#card-form div.payment-two-cols",
    "CARD_DATA_NAME": 'input[data-stripe="name"]',
    "CARD_DATA_ADDRESS_LINE1": 'input[data-stripe="address_line1"]',
    "CARD_DATA_ADDRESS_LINE2": 'input[data-stripe="address_line2"]',
    "CARD_DATA_CITY": 'input[data-stripe="address_city"]',
    "CARD_DATA_ZIP": 'input[data-stripe="address_zip"]',
    "CARD_DATA_CARD_NO": 'input[id="num"]',
    "CARD_DATA_STATE": 'div[id="zf-select-pay-state"]',
    "CARD_DATA_EXP_MONTH": 'div[id="zf-select-em"]',
    "CARD_DATA_EXP_YEAR": 'div[id="zf-select-ey"]',
    "CARD_DATA_CVV_NO": 'input[id="cv"]',
    "CARD_DATA_SUBMIT_BUTTON": 'input[value="Submit Payment"]',
}


class BaldorLoginPage(PasswordBasedLoginPage):
    """
    Alsco login module
    """

    SELECTOR_USERNAME_TEXTBOX = 'input[id="EmailLoginForm_email"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="EmailLoginForm_password"]'
    SELECTOR_LOGIN_BUTTON = 'input[value="SIGN IN"]'
    SELECTOR_ERROR_MESSAGE_TEXT = "div.errorMessage"


class BaldorPaymentsPage:
    """Payments"""

    def __init__(
        self,
        run,
        driver,
        invoice_element: WebElement,
        invoice: dict,
        payment_data: dict,
    ):
        self.run = run
        self.driver = driver
        self.invoice_element = invoice_element
        self.invoice = invoice
        self.payment_data = payment_data

    def do_payment(self) -> VendorPayment:
        vendor_payment = VendorPayment(run=self.run)
        # validating total_due_amount with credit_limit
        invoice_amount, status = self.get_invoice_amount_and_status()
        if invoice_amount < self.payment_data["total_amount"] or status != "Shipped":
            raise ContextualError(
                code=ErrorCode.VP_INVOICE_AMOUNT_MISMATCHED_FAILED.ident,  # pylint: disable=no-member
                message=ErrorCode.VP_INVOICE_AMOUNT_MISMATCHED_FAILED.message.format(  # pylint: disable=no-member
                    invoice_id=self.invoice["invoice_number"]
                ),
            )  # pylint: disable=no-member
        self.driver.execute_script("window.scroll(0, 0);")
        sleep(4)
        self.driver.find_element_by_xpath(
            PAYMENT_PAGE_LOCATORS["PAYMENT_BUTTON"]
        ).click()
        explicit_wait_till_visibility(
            self.driver,
            self.driver.find_element_by_css_selector(
                PAYMENT_PAGE_LOCATORS["PAYMENTS_TAB"]
            ),
            msg="Payment tabs",
        )
        self.driver.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_TAB"]
        ).click()
        payment_ele = self.driver.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_DATA_FORM"]
        )
        card_details = self.payment_data["card_details"]
        payment_ele.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_DATA_NAME"]
        ).send_keys(card_details["name"])
        billing_address = card_details["billing_address"]
        payment_ele.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_DATA_ADDRESS_LINE1"]
        ).send_keys(billing_address["street1"])
        payment_ele.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_DATA_ADDRESS_LINE2"]
        ).send_keys(billing_address["street2"])
        payment_ele.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_DATA_CITY"]
        ).send_keys(billing_address["city"])
        payment_ele.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_DATA_ZIP"]
        ).send_keys(billing_address["zip"])
        payment_ele.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_DATA_CARD_NO"]
        ).send_keys(card_details["card_number"])
        sleep(3)
        expiry_month_select = payment_ele.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_DATA_STATE"]
        )
        expiry_month_select.click()
        expiry_month_select.send_keys(card_details["state"])
        sleep(3)
        expiry_month_select = payment_ele.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_DATA_EXP_MONTH"]
        )
        expiry_month_select.click()
        expiry_month_select.send_keys(card_details["expiry_month"])
        sleep(3)
        expiry_year_select = payment_ele.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_DATA_EXP_MONTH"]
        )
        expiry_year_select.click()
        expiry_year_select.send_keys(card_details["expiry_year"])
        sleep(3)
        payment_ele.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_DATA_CVV_NO"]
        ).send_keys(card_details["cvv_number"])
        self.driver.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CARD_DATA_SUBMIT_BUTTON"]
        ).click()

        # BillPayCoreClient()
        # TODO : integration with bill pay is remaining, would improvise post discussion with arturo
        return vendor_payment

    def get_invoice_amount_and_status(self):
        """
        Get invoice amount and status from table row.
        """

        # Table column-index, title mapping
        column_index_title_mapping = {
            "CLICK TO PAY": 0,
            "ORDER": 1,
            "TOTAL": 2,
            "OPEN": 3,
            "CLOSED": 4,
            "CONFIRMATION #": 5,
            "CREDIT MEMO": 6,
            "DESCRIPTION": 7,
            "STATUS": 9,
        }
        invoice_amount = 0
        status = None
        row_data = self.invoice_element.find_element_by_xpath(
            ".."
        ).find_elements_by_tag_name("td")
        for index, column in enumerate(row_data):
            if index == column_index_title_mapping["OPEN"]:
                invoice_amount = float(column.text.replace("$", ""))
            elif index == column_index_title_mapping["STATUS"]:
                status = column.text
        return invoice_amount, status


class BaldorRunner(VendorDocumentDownloadInterface):
    """Runner Class for Baldor"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = BaldorLoginPage(self.driver)
        self.invoices_page_url = (
            "https://www.baldorfood.com/account-home/invoices-and-orders"
        )

    def _login(self):
        """
        Login to baldor
        :return: Nothing
        """
        login_url = "https://www.baldorfood.com/users/default/new-login"
        get_url(self.driver, login_url)
        self.login_page.login(self.run.job.username, self.run.job.password)

    def start_payment_flow(self, run: Run) -> List[VendorPayment]:
        """
        Initiates the invoice payment Workflow
        :param run: Run Object
        :return: Returns the status of payment
        """
        vendor_payments = []
        try:
            self._login()
            get_url(self.driver, self.invoices_page_url)
            vendor_payments += self._do_payment()

        finally:
            self._quit_driver()

        return vendor_payments

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files.
        """

        return []

    def login_flow(self, run: Run):
        self._login()

    def _do_payment(self):
        """
        Chooses the invoices to be paid based on the run request params
        :return: Returns the status of payments
        """
        vendor_payments = []
        self.driver.find_element_by_css_selector(".only-all-invoices-js").click()
        for payment_invoice in self.run.request_parameters.get("payments", []):
            try:
                explicit_wait_till_visibility(
                    self.driver,
                    self.get_all_invoices_list(),
                    msg="Invoices list",
                    timeout=30,
                )
                for invoice in payment_invoice["invoices"]:
                    invoice_id = invoice["invoice_number"]
                    explicit_wait_till_visibility(
                        self.driver,
                        self.get_invoice_list(invoice_id),
                        msg="Invoice element",
                    )
                    sleep(4)
                    invoice_data = self.get_invoice_list(invoice_id)
                    if not invoice_data:
                        raise ContextualError(
                            code=ErrorCode.VP_INVOICE_SELECTION_FAILED.ident,  # pylint: disable=no-member
                            message=ErrorCode.VP_INVOICE_SELECTION_FAILED.message.format(  # pylint: disable=no-member
                                invoice_id=invoice_id
                            ),
                        )  # pylint: disable=no-member
                    explicit_wait_till_visibility(
                        self.driver,
                        self.get_invoice_data(invoice_id),
                        msg="Invoices list",
                        timeout=30,
                    )
                    self.driver.execute_script(
                        "arguments[0].click();", self.get_invoice_data(invoice_id)
                    )
                    vendor_payments.append(
                        BaldorPaymentsPage(
                            self.run,
                            self.driver,
                            invoice_data,
                            invoice,
                            payment_invoice,
                        ).do_payment()
                    )

            except ContextualError as exc:
                vendor_payment = VendorPayment(
                    run=self.run, payment_status=PaymentStatus.FAILED
                )
                vendor_payment.failure_issue = Issue.build_from_exception(exc)
                vendor_payment.save()
                vendor_payments.append(vendor_payment)
                continue

        return vendor_payments

    def get_invoice_data(self, invoice_id):
        return self.driver.find_element_by_css_selector(
            f'label[for="order_{invoice_id}"]'
        )

    def get_invoice_list(self, invoice_id):
        return self.driver.find_element_by_xpath(
            f'//td[contains(text(),"{invoice_id}")]'
        )

    def get_all_invoices_list(self) -> WebElement:
        return self.driver.find_element_by_css_selector("table.items")
