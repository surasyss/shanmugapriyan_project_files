import logging
from typing import List

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.base import PasswordBasedLoginPage, AccountingPaymentUpdateInterface
from apps.adapters.helpers.helper import sleep
from apps.adapters.helpers.webdriver_helper import (
    explicit_wait_till_visibility,
    scroll_down_to_element,
    find_element_in_list_by_text,
    hover_over_element,
    set_implicit_timeout,
    get_url,
)
from apps.error_codes import ErrorCode
from apps.jobconfig.models import PIQMapping
from apps.runs.models import Run, CheckRun, CheckRunExists, CheckRunDisabled
from integrator import settings
from spices.django3.coreobjects.models import Location, Vendor, BankAccount
from spices.services import ContextualError

# pylint: disable=no-member

TIMEOUT = 20
LOGGER = logging.getLogger("apps.adapters.accounting.r365")

MANUAL_PAYMENT_URL_SEGMENT = (
    "/form/APPaymentForm/00000000-0000-0000-0000-000000000000?Reference=TopRibbon"
)

HOME_PAGE_LOCATORS = {
    "DIALOGUE_CONTAINER": "div._pendo-guide-container_",
    "DIALOGUE_CONTAINER_CLOSE_BUTTON": "button._pendo-close-guide_",
    "HOME_VENDOR_MENU": 'ul.navbar-nav>li[id="Vendor"]',
    "HOME_VENDOR_MENU_MANUAL_PAYMENT_ITEM": 'ul.dropdown-menu>li[id="VendorManualPayment"]',
}

PAYMENT_PAGE_LOCATORS = {
    "NAVBAR_APPROVE_MENU": 'ul.nav.navbar-nav>li[data-testid="approveRibbonMenu"]',
    "NAVBAR_APPROVE_MENU_APPROVE_ITEM": 'ul.dropdown-menu>li[ng-show="ribbon.flags.showApprove"]',
    "NAVBAR_APPROVE_MENU_APPROVE_NEW_ITEM": 'ul.dropdown-menu>li[ng-show="ribbon.flags.showApproveAndNew"]',
    "CHECKING_ACCOUNT_DROPDOWN": "glaccountDropdown_input",
    "CHECKING_ACCOUNT_DROPDOWN_OPTIONS": 'ul[id="glaccountDropdown_listbox"]>li>span',
    "CHECKING_ACCOUNT_LISTBOX": 'ul[id="glaccountDropdown_listbox"]',
    "CHECKING_ACCOUNT_DROPDOWN_ARROW": '//span[@aria-controls="glaccountDropdown_listbox"][@class="k-icon k-i-arrow-s"]',
    "AMOUNT_TEXTBOX": "APPaymentAmount",
    "LOCATION_DROPDOWN": "APPaymentLocation_input",
    "LOCATION_DROPDOWN_OPTIONS": 'ul[id="APPaymentLocation_listbox"]>li>span',
    "LOCATION_LISTBOX": 'ul[id="APPaymentLocation_listbox"]',
    "LOCATION_DROPDOWN_ARROW": '//span[@aria-controls="APPaymentLocation_listbox"][@class="k-icon k-i-arrow-s"]',
    "NUMBER_TEXTBOX": "APPaymentNumber",
    "VENDOR_DROPDOWN": "APPaymentCompany_input",
    "VENDOR_DROPDOWN_OPTIONS": 'ul[id="APPaymentCompany_listbox"]>li',
    "VENDOR_LISTBOX": 'ul[id="APPaymentCompany_listbox"]',
    "VENDOR_DROPDOWN_ARROW": '//span[@aria-controls="APPaymentCompany_listbox"][@class="k-icon k-i-arrow-s"]',
    "VENDOR_DROPDOWN_LOADING": '//span[@aria-controls="APPaymentCompany_listbox"][contains(@class, "k-loading")]',
    "DATE_TEXTBOX": "APPaymentDate",
    "COMMENT_TEXTAREA": "APPaymentComment",
    "APPLY_BUTTON": '//ul[contains(@class,"k-tabstrip-items")]/li/span[text()="Apply"]',
    "TABLE_HEADER_DATE": 'div[id="APPaymentApplyGrid"]>table>thead>tr>th[data-field="date"]',
    "TABLE_HEADER_TYPE": 'div[id="APPaymentApplyGrid"]>table>thead>tr>th[data-field="transactionType"]',
    "TABLE_HEADER_NUMBER": 'div[id="APPaymentApplyGrid"]>table>thead>tr>th[data-field="number"]',
    "TABLE_HEADER_LOCATION": 'div[id="APPaymentApplyGrid"]>table>thead>tr>th[data-field="location"]',
    "TABLE_HEADER_TOTAL": 'div[id="APPaymentApplyGrid"]>table>thead>tr>th[data-field="transactionTotal"]',
    "TABLE_HEADER_DISCOUNT_AMOUNT": 'div[id="APPaymentApplyGrid"]>table>thead>tr>th[data-field="discountAmount"]',
    "TABLE_HEADER_AMOUNT_REMAINING": 'div[id="APPaymentApplyGrid"]>table>thead>tr>th[data-field="amountRemaining"]',
    "TABLE_HEADER_APPLY_DATE": 'div[id="APPaymentApplyGrid"]>table>thead>tr>th[data-field="applyDate"]',
    "TABLE_HEADER_APPLY_AMOUNT": 'div[id="APPaymentApplyGrid"]>table>thead>tr>th[data-field="applyAmount"]',
    "TABLE_HEADER_APPLY": 'div[id="APPaymentApplyGrid"]>table>thead>tr>th[data-field="apply"]',
    "TABLE_ROWS": 'div[id="APPaymentApplyGrid"]>div.k-grid-content>table>tbody>tr',
    "APPLY_CHECKBOXES": 'div[id="APPaymentApplyGrid"] input.check-apply-amount-checkbox',
    "APPLY_TOTAL_AMOUNT_LABELS": "div.apply-totals-container>div.row>div.text-right>strong",
    "TOAST_LABEL": 'div[id="toast-container"] div.toast-message',
    "TOAST_CLOSE_BUTTON": 'div[id="toast-container"] button.toast-close-button',
}


class R365LoginPage(PasswordBasedLoginPage):
    SELECTOR_USERNAME_TEXTBOX = 'input[id="userIdField"]'
    SELECTOR_PASSWORD_TEXTBOX = 'input[id="userPasswordField"]'
    SELECTOR_LOGIN_BUTTON = 'button[data-testid="signInButton"]'


class R365HomePage:
    """Restaurant 365 Home page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def get_navbar_vendor_menu(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["HOME_VENDOR_MENU"]
        )

    def _get_navbar_vendor_menu_manual_payment_item(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["HOME_VENDOR_MENU_MANUAL_PAYMENT_ITEM"]
        )

    def get_dialogue_container(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["DIALOGUE_CONTAINER"]
        )

    def get_dialogue_container_close_button(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_LOCATORS["DIALOGUE_CONTAINER_CLOSE_BUTTON"]
        )

    def go_to_manual_payment_page(self, run: Run):
        LOGGER.info("Going to Manual Payment Page...")
        manual_payment_url = f"{run.job.login_url}#{MANUAL_PAYMENT_URL_SEGMENT}"
        get_url(self.driver, manual_payment_url)

    def check_popup(self):
        try:
            while True:
                LOGGER.info("Checking Popup Loop")
                explicit_wait_till_visibility(
                    self.driver,
                    self.get_dialogue_container(),
                    2,
                    msg="Dialogue Container",
                )
                self.get_dialogue_container_close_button().click()
                LOGGER.info("Popup Closed")
        except (TimeoutException, NoSuchElementException):
            LOGGER.info("Exiting Check Popup Loop")
            pass


class R365ManualPaymentPage:
    """Restaurant 365 Manual Payment page action methods come here."""

    def __init__(self, driver):
        self.driver = driver

    def _get_navbar_approve_menu(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["NAVBAR_APPROVE_MENU"]
        )

    def _get_navbar_approve_menu_approve_new_item(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["NAVBAR_APPROVE_MENU_APPROVE_NEW_ITEM"]
        )

    def _get_navbar_approve_menu_approve_item(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["NAVBAR_APPROVE_MENU_APPROVE_ITEM"]
        )

    def _get_checking_account_dropdown(self) -> WebElement:
        return self.driver.find_element_by_name(
            PAYMENT_PAGE_LOCATORS["CHECKING_ACCOUNT_DROPDOWN"]
        )

    def _get_checking_account_dropdown_options(self) -> List[WebElement]:
        return self.driver.find_elements_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CHECKING_ACCOUNT_DROPDOWN_OPTIONS"]
        )

    def _get_nth_checking_account_dropdown_option(self, index: int) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CHECKING_ACCOUNT_DROPDOWN_OPTIONS"]
        )[index]

    def _get_checking_account_dropdown_arrow(self) -> WebElement:
        return self.driver.find_element_by_xpath(
            PAYMENT_PAGE_LOCATORS["CHECKING_ACCOUNT_DROPDOWN_ARROW"]
        )

    def _get_checking_account_listbox(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["CHECKING_ACCOUNT_LISTBOX"]
        )

    def _get_amount_textbox(self) -> WebElement:
        return self.driver.find_element_by_name(PAYMENT_PAGE_LOCATORS["AMOUNT_TEXTBOX"])

    def _get_location_dropdown(self) -> WebElement:
        return self.driver.find_element_by_name(
            PAYMENT_PAGE_LOCATORS["LOCATION_DROPDOWN"]
        )

    def _get_location_dropdown_options(self) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            PAYMENT_PAGE_LOCATORS["LOCATION_DROPDOWN_OPTIONS"]
        )

    def _get_nth_location_dropdown_option(self, index: int) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            PAYMENT_PAGE_LOCATORS["LOCATION_DROPDOWN_OPTIONS"]
        )[index]

    def _get_location_dropdown_arrow(self) -> WebElement:
        return self.driver.find_element_by_xpath(
            PAYMENT_PAGE_LOCATORS["LOCATION_DROPDOWN_ARROW"]
        )

    def _get_location_listbox(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["LOCATION_LISTBOX"]
        )

    def _get_number_textbox(self) -> WebElement:
        return self.driver.find_element_by_name(PAYMENT_PAGE_LOCATORS["NUMBER_TEXTBOX"])

    def _get_vendor_dropdown(self) -> WebElement:
        return self.driver.find_element_by_name(
            PAYMENT_PAGE_LOCATORS["VENDOR_DROPDOWN"]
        )

    def _get_vendor_dropdown_options(self) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            PAYMENT_PAGE_LOCATORS["VENDOR_DROPDOWN_OPTIONS"]
        )

    def _get_nth_vendor_dropdown_option(self, index: int) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            PAYMENT_PAGE_LOCATORS["VENDOR_DROPDOWN_OPTIONS"]
        )[index]

    def _get_vendor_dropdown_arrow(self) -> WebElement:
        return self.driver.find_element_by_xpath(
            PAYMENT_PAGE_LOCATORS["VENDOR_DROPDOWN_ARROW"]
        )

    def _get_vendor_dropdown_loading(self) -> WebElement:
        return self.driver.find_element_by_xpath(
            PAYMENT_PAGE_LOCATORS["VENDOR_DROPDOWN_LOADING"]
        )

    def _get_vendor_listbox(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["VENDOR_LISTBOX"]
        )

    def _get_date_textbox(self) -> WebElement:
        return self.driver.find_element_by_name(PAYMENT_PAGE_LOCATORS["DATE_TEXTBOX"])

    def _get_comment_textarea(self) -> WebElement:
        return self.driver.find_element_by_name(
            PAYMENT_PAGE_LOCATORS["COMMENT_TEXTAREA"]
        )

    def _get_apply_button(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["APPLY_BUTTON"]
        )

    def _get_table_rows(self) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            PAYMENT_PAGE_LOCATORS["TABLE_ROWS"]
        )

    def _get_nth_table_row_apply_checkbox(self, index: int) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            PAYMENT_PAGE_LOCATORS["APPLY_CHECKBOXES"]
        )[index]

    def _get_apply_amount_total(self) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            PAYMENT_PAGE_LOCATORS["APPLY_TOTAL_AMOUNT_LABELS"]
        )[0]

    def _get_apply_applied_amount(self) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            PAYMENT_PAGE_LOCATORS["APPLY_TOTAL_AMOUNT_LABELS"]
        )[1]

    def _get_apply_amount_remaining(self) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            PAYMENT_PAGE_LOCATORS["APPLY_TOTAL_AMOUNT_LABELS"]
        )[3]

    def _get_toast_message(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["TOAST_LABEL"]
        )

    def _get_toast_close_button(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            PAYMENT_PAGE_LOCATORS["TOAST_CLOSE_BUTTON"]
        )

    def _close_toast_message(self):
        try:
            set_implicit_timeout(self.driver, 2)
            explicit_wait_till_visibility(
                self.driver,
                self._get_toast_close_button(),
                timeout=2,
                msg="Toast Message",
            )
            self._get_toast_close_button().click()
            set_implicit_timeout(self.driver, 15)
        except (NoSuchElementException, TimeoutException):
            set_implicit_timeout(self.driver, 15)
            LOGGER.warning(f"Toast Message not found!")

    def _wait_for_vendor_dropdown_options(self) -> WebElement:
        dd_options = self._get_vendor_dropdown_options()
        index = 0
        while len(dd_options) != 1 and index < 20:
            try:
                explicit_wait_till_visibility(
                    self.driver,
                    self._get_vendor_listbox(),
                    timeout=5,
                    msg="Vendor Listbox",
                )
                sleep(1)
            except (NoSuchElementException, TimeoutException):
                LOGGER.info("Clicking Vendor DropDown Arrow")
                self._get_vendor_dropdown_arrow().click()
                explicit_wait_till_visibility(
                    self.driver, self._get_vendor_listbox(), msg="Vendor Listbox"
                )

            dd_options = self._get_vendor_dropdown_options()
            LOGGER.info(
                f"Waiting for Vendor DropDown to update. DropDowns visible: {len(dd_options)}"
            )
            index += 1

    def _wait_for_location_dropdown_options(self) -> WebElement:
        dd_options = self._get_location_dropdown_options()
        index = 0
        while len(dd_options) != 1 and index < 20:
            try:
                explicit_wait_till_visibility(
                    self.driver,
                    self._get_location_listbox(),
                    timeout=5,
                    msg="Location Listbox",
                )
                sleep(1)
            except (NoSuchElementException, TimeoutException):
                LOGGER.info("Clicking Location DropDown Arrow")
                self._get_location_dropdown_arrow().click()
                explicit_wait_till_visibility(
                    self.driver, self._get_location_listbox(), msg="Location Listbox"
                )

            dd_options = self._get_location_dropdown_options()
            LOGGER.info(
                f"Waiting for Location DropDown to update. DropDowns visible: {len(dd_options)}"
            )
            index += 1

    def _wait_for_checking_acct_dropdown_options(self) -> WebElement:
        dd_options = self._get_checking_account_dropdown_options()
        index = 0
        while len(dd_options) != 1 and index < 20:
            try:
                explicit_wait_till_visibility(
                    self.driver,
                    self._get_checking_account_listbox(),
                    timeout=5,
                    msg="Checking Account Listbox",
                )
                sleep(1)
            except (NoSuchElementException, TimeoutException):
                LOGGER.info("Clicking Location DropDown Arrow")
                self._get_checking_account_dropdown_arrow().click()
                explicit_wait_till_visibility(
                    self.driver,
                    self._get_checking_account_listbox(),
                    msg="Checking Account Listbox",
                )

            LOGGER.info("Waiting for Checking Account DropDown to update")
            dd_options = self._get_checking_account_dropdown_options()
            index += 1

    def _wait_for_loaders(self):
        explicit_wait_till_visibility(
            self.driver,
            self._get_location_dropdown_arrow(),
            TIMEOUT,
            msg="Location DropDown Arrow",
        )
        explicit_wait_till_visibility(
            self.driver,
            self._get_checking_account_dropdown_arrow(),
            TIMEOUT,
            msg="Checking Account DropDown Arrow",
        )
        try:
            explicit_wait_till_visibility(
                self.driver,
                self._get_vendor_dropdown_arrow(),
                TIMEOUT,  # This failed once
                msg="Vendor DropDown Arrow",
            )
        except (NoSuchElementException, TimeoutException):
            LOGGER.warning(
                f"_get_vendor_dropdown_arrow() not visible. Ignoring the exception"
            )
            pass

    def _find_checking_account(self, text: str) -> WebElement:
        LOGGER.info('Finding "%s" text in the list of Checking Accounts', text)
        for elem in self._get_checking_account_dropdown_options():
            try:
                if elem.text.upper().strip() == text.upper().strip():
                    LOGGER.info('Found "%s" in the list of Checking Accounts', text)
                    return elem

                if elem.text.split(" - ", 1)[1].upper().strip() == text.upper().strip():
                    LOGGER.info('Found "%s" in the list of Checking Accounts', text)
                    return elem
            except IndexError as error:
                LOGGER.error(error)
        return None

    def _select_checking_account(self, check_run_id: int, bank_account: str):
        """Returns True in case of no error & False otherwise"""
        try:
            LOGGER.info(
                f"[tag:WER365SCA10] Selecting Checking Account - {bank_account}"
            )
            LOGGER.info(
                f"[tag:WER365SCA20] Clearing Checking Account DropDown & Sending {bank_account}"
            )
            self._get_checking_account_dropdown().clear()
            self._close_toast_message()
            self._get_checking_account_dropdown().send_keys(bank_account)
            self._wait_for_checking_acct_dropdown_options()
            explicit_wait_till_visibility(
                self.driver,
                self._get_checking_account_listbox(),
                TIMEOUT,
                msg="Checking Account Listbox",
            )
            select_elem = self._find_checking_account(bank_account)

            if not select_elem:
                LOGGER.warning(
                    f"[tag:WER365SCA30] Bank Account ({bank_account}) not found in r365"
                )
                raise ContextualError(
                    code=ErrorCode.PE_BANK_ACC_NOT_FOUND.ident,
                    message=ErrorCode.PE_BANK_ACC_NOT_FOUND.message.format(
                        bank_account=bank_account
                    ),
                    params={"checkrun_id": check_run_id},
                )

            LOGGER.info(
                f"[tag:WER365SCA40] Clicking on the searched element: {select_elem.text}"
            )
            select_elem.click()
            self._wait_for_loaders()
            return
        except NoSuchElementException as exception:
            LOGGER.warning(
                f"[tag:WER365SCA50] Bank Account not found - {bank_account}: {exception}",
                exc_info=True,
            )
            raise ContextualError(
                code=ErrorCode.PE_BANK_ACC_NOT_FOUND.ident,
                message=ErrorCode.PE_BANK_ACC_NOT_FOUND.message.format(
                    bank_account=bank_account
                ),
                params={"checkrun_id": check_run_id},
            ) from exception
        except Exception as exception:
            LOGGER.exception(
                f"[tag:WER365SCA60] Something went wrong while selecting Bank Account ({bank_account}): {exception}"
            )
            raise ContextualError(
                code=ErrorCode.PE_BANK_ACC_SELECTION_FAILED.ident,
                message=ErrorCode.PE_BANK_ACC_SELECTION_FAILED.message.format(
                    bank_account=bank_account
                ),
                params={"checkrun_id": check_run_id},
            ) from exception

    def _select_vendor(self, check_run_id: int, vendor_id: str):
        """Returns True in case of no error & False otherwise"""
        LOGGER.info(f"[tag:WER365SV10] Selecting Vendor - {vendor_id}")
        try:
            explicit_wait_till_visibility(
                self.driver,
                self._get_vendor_dropdown_arrow(),
                TIMEOUT,
                msg="Vendor DropDown Arrow",
            )
        except (NoSuchElementException, TimeoutException):
            LOGGER.warning(
                f"[tag:WER365SV20]  _get_vendor_dropdown_arrow() not visible. Ignoring the exception"
            )

        try:
            self._search_vendor_special_case(vendor_id)
            explicit_wait_till_visibility(
                self.driver,
                self._get_vendor_dropdown_arrow(),
                TIMEOUT,
                msg="Vendor DropDown Arrow",
            )
            self._wait_for_vendor_dropdown_options()
            select_elem = find_element_in_list_by_text(
                self._get_vendor_dropdown_options(), vendor_id
            )

            if not select_elem:
                LOGGER.warning(
                    f"[tag:WER365SV30] Vendor ({vendor_id}) not found in r365"
                )
                raise ContextualError(
                    code=ErrorCode.PE_VENDOR_NOT_FOUND.ident,
                    message=ErrorCode.PE_VENDOR_NOT_FOUND.message.format(
                        vendor_name=vendor_id
                    ),
                    params={"checkrun_id": check_run_id},
                )

            explicit_wait_till_visibility(
                self.driver,
                select_elem,
                TIMEOUT,
                msg=f"Vendor DropDown Option: {vendor_id}",
            )
            LOGGER.info(
                f"[tag:WER365SV40] Clicking on the searched element: {select_elem.text}"
            )
            select_elem.click()  # Got StaleElementReferenceException once
            self._wait_for_loaders()
            return

        except NoSuchElementException as exception:
            LOGGER.warning(
                f"[tag:WER365SV50] Vendor ({vendor_id}) not found in r365 - {exception}",
                exc_info=True,
            )
            raise ContextualError(
                code=ErrorCode.PE_VENDOR_NOT_FOUND.ident,
                message=ErrorCode.PE_VENDOR_NOT_FOUND.message.format(
                    vendor_name=vendor_id
                ),
                params={"checkrun_id": check_run_id},
            )
        except Exception as exception:
            LOGGER.exception(
                f"[tag:WER365SV60] Vendor ({vendor_id}) not found in r365 - {exception}"
            )
            raise ContextualError(
                code=ErrorCode.PE_VENDOR_SELECTION_FAILED.ident,
                message=ErrorCode.PE_VENDOR_SELECTION_FAILED.message.format(
                    vendor_name=vendor_id
                ),
                params={"checkrun_id": check_run_id},
            )

    def _search_vendor_special_case(self, vendor_id: str):
        """Special Handling for Vendors with Single Quote. This is a bug in R365"""
        LOGGER.debug(f"Sending {vendor_id} in Vendor DropDown")
        if "'" in vendor_id:
            vendor_id = vendor_id.split("'", 1)[0]

        self._get_vendor_dropdown().send_keys(vendor_id)

    def _find_location(self, text: str) -> WebElement:
        LOGGER.info('Finding "%s" text in the list of Locations', text)
        for elem in self._get_location_dropdown_options():
            try:
                if elem.text.upper().strip() == text.upper().strip():
                    LOGGER.info('Found "%s" in the list of Locations', text)
                    return elem
                if len(self._get_location_dropdown_options()) == 1:
                    return elem
            except IndexError as error:
                LOGGER.error(error)
        return None

    def _select_location(self, check_run_id: int, location_id: str) -> str:
        """Returns True in case of no error & False otherwise"""
        LOGGER.info(f"[tag:WER365SL10] Selecting Location - {location_id}")
        LOGGER.debug("[tag:WER365SL20] Clicking on Location DropDown Arrow")
        try:
            LOGGER.debug(
                f"[tag:WER365SL30] Clearing Location DropDown & Sending {location_id}"
            )
            self._get_location_dropdown().clear()
            self._get_location_dropdown().send_keys(location_id)
            self._wait_for_location_dropdown_options()

            explicit_wait_till_visibility(
                self.driver,
                self._get_location_listbox(),
                TIMEOUT,
                msg="Location ListBox",
            )
            select_elem = self._find_location(location_id)

            if not select_elem:
                LOGGER.warning(f"[tag:WER365SL40] Location ({location_id}) not found")
                raise ContextualError(
                    code=ErrorCode.PE_LOCATION_NOT_FOUND.ident,
                    message=ErrorCode.PE_LOCATION_NOT_FOUND.message.format(
                        location_name=location_id
                    ),
                    params={"checkrun_id": check_run_id},
                )

            explicit_wait_till_visibility(
                self.driver,
                select_elem,
                TIMEOUT,
                msg=f"Location ListBox option: {location_id}",
            )
            select_location = select_elem.text
            LOGGER.info(
                f"[tag:WER365SL50] Clicking on the searched element: {select_location}"
            )
            select_elem.click()
            self._close_toast_message()
            self._wait_for_loaders()
            return select_location
        except NoSuchElementException as exception:
            LOGGER.warning(
                f"[tag:WER365SL60] Location ({location_id}) not found - {exception}",
                exc_info=True,
            )
            raise ContextualError(
                code=ErrorCode.PE_LOCATION_NOT_FOUND.ident,
                message=ErrorCode.PE_LOCATION_NOT_FOUND.message.format(
                    location_name=location_id
                ),
                params={"checkrun_id": check_run_id},
            ) from exception
        except Exception as exception:
            LOGGER.exception(
                f"[tag:WER365SL70] Something went wrong while selecting Location ({location_id}) in r365 - {exception}"
            )
            raise ContextualError(
                code=ErrorCode.PE_LOCATION_SELECTION_FAILED.ident,
                message=ErrorCode.PE_LOCATION_SELECTION_FAILED.message.format(
                    location_name=location_id
                ),
                params={"checkrun_id": check_run_id},
            ) from exception

    def fill_manual_payment_form(self, check_run_dict: dict):
        """Returns True in case of no error & False otherwise"""
        LOGGER.info(f"[tag:WER365FMP10] Filling Manual Payment Form - {check_run_dict}")
        self._wait_for_loaders()
        check_run_id = check_run_dict["chequerun_id"]

        selected_location = self._select_location(
            check_run_id, check_run_dict["location_id"]
        )
        self._select_checking_account(check_run_id, check_run_dict["bank_account"])
        self._select_vendor(check_run_id, check_run_dict["vendor_id"])

        LOGGER.info(
            f'[tag:WER365FMP20] Clearing Number textbox & Entering {check_run_dict["payment_number"]}'
        )
        self._get_number_textbox().clear()
        self._get_number_textbox().send_keys("PIQ_" + check_run_dict["payment_number"])

        LOGGER.info(
            f'[tag:WER365FMP30] Entering {check_run_dict["payment_total"]} in Amount textbox'
        )
        self._get_amount_textbox().click()
        self._get_amount_textbox().send_keys(str(check_run_dict["payment_total"]))

        LOGGER.info(
            f'[tag:WER365FMP40] Entering {check_run_dict["payment_date"]} in Date textbox'
        )
        self._get_date_textbox().click()
        self._get_date_textbox().send_keys(check_run_dict["payment_date"])

        LOGGER.info(
            f'[tag:WER365FMP50] Entering "Created with PlateIQ!" in Comment textarea'
        )
        self._get_comment_textarea().clear()
        self._get_comment_textarea().send_keys("Created with PlateIQ!")

        # Checking for invoices to be applied
        invoice_list = self._get_invoice_table(
            check_run_dict["invoices"], selected_location
        )
        if not invoice_list:
            expected_invoices = [
                invoice["invoice_number"] for invoice in check_run_dict["invoices"]
            ]
            expected_invoices = ", ".join(expected_invoices)
            LOGGER.warning(
                f"[tag:WER365FMP60] No invoice found in r365. Expected invoices: {expected_invoices}"
            )

            raise ContextualError(
                code=ErrorCode.PE_INVOICE_NOT_FOUND.ident,
                message=ErrorCode.PE_INVOICE_NOT_FOUND.message.format(
                    invoice_numbers=expected_invoices
                ),
                params={"checkrun_id": check_run_id},
            )

        self._select_invoices(check_run_id, invoice_list)

    def _get_invoice_table(self, invoices_list: list, selected_location: str) -> List:
        LOGGER.info(
            f"Fetching Invoice Table data - Expecting invoices: {invoices_list}"
        )
        invoice_list_to_be_selected = []
        rows = self._get_table_rows()
        for index, row in enumerate(rows[0:]):
            invoice_number = row.find_elements_by_tag_name("td")[2].text
            location = row.find_elements_by_tag_name("td")[3].text
            invoice_row = {
                "index": index,
                "invoice_date": row.find_elements_by_tag_name("td")[0].text,
                "type": row.find_elements_by_tag_name("td")[1].text,
                "invoice_number": invoice_number,
                "location": location,
                "total": row.find_elements_by_tag_name("td")[4].text,
                "discount_amount": row.find_elements_by_tag_name("td")[5].text,
                "amount_remaining": row.find_elements_by_tag_name("td")[6].text,
                "apply_date": row.find_elements_by_tag_name("td")[7].text,
                "apply_amount": row.find_elements_by_tag_name("td")[8].text,
            }
            LOGGER.debug(f"Invoice at index: {index}: {invoice_row}")

            for invoice in invoices_list:
                if (
                    invoice_number in invoice["invoice_number"]
                    and location.upper() in selected_location.upper()
                ):
                    LOGGER.debug(f"Invoice: {invoice_number} found!")
                    invoice_list_to_be_selected.append(invoice_row)

            if invoice_list_to_be_selected.__len__() == invoices_list.__len__():
                LOGGER.info(f"All invoices found. Count: {invoices_list.__len__()}")
                break

        return invoice_list_to_be_selected

    def _select_invoices(
        self, check_run_id: int, invoice_list_to_be_selected: list
    ) -> bool:
        try:
            for item in invoice_list_to_be_selected:
                LOGGER.info(f'Selecting invoice at index: {item["index"]}')
                scroll_down_to_element(
                    self.driver, self._get_nth_table_row_apply_checkbox(item["index"])
                )
                self._get_nth_table_row_apply_checkbox(item["index"]).click()
        except Exception as exception:
            LOGGER.exception(f"Failed while selecting invoices - {exception}")
            raise ContextualError(
                code=ErrorCode.PE_INVOICE_SELECTION_FAILED.ident,
                message=ErrorCode.PE_INVOICE_SELECTION_FAILED.message,
                params={"checkrun_id": check_run_id},
            ) from exception

    def validate_manual_payment(self, check_run_id: int, amount: float):
        """Returns True in case of no error & False otherwise"""
        amount_in_str = "{0:,.2f}".format(amount)
        LOGGER.info(f"Validating Total Amount. Expected: {amount_in_str}")
        apply_total_amount = self._get_apply_amount_total().text
        apply_applied_amount = self._get_apply_applied_amount().text
        apply_remaining_amount = self._get_apply_amount_remaining().text

        post_error_msg = None
        if apply_total_amount != amount_in_str:
            post_error_msg = (
                f"Total amount mismatch. Expected {amount_in_str}, actual: {apply_total_amount}. "
                f"Probably Invoice(s) not found."
            )
        elif apply_applied_amount != amount_in_str:
            post_error_msg = (
                f"Applied amount mismatch. Expected {amount_in_str}, actual: {apply_applied_amount}. "
                f"Probably few invoice(s) are missing."
            )
        elif apply_remaining_amount != "0.00":
            post_error_msg = (
                f"Remaining amount mismatch. Expected {amount_in_str}, actual: "
                f"{apply_remaining_amount} Probably few invoice(s) are missing."
            )

        if post_error_msg:
            settings.PIQ_CORE_CLIENT.post_billpay_cheque_error(
                check_run_id, post_error_msg
            )
            LOGGER.warning(post_error_msg)
            raise ContextualError(
                code=ErrorCode.PE_VALIDATION_AMOUNT_MISMATCH.ident,
                message=post_error_msg,
                params={"checkrun_id": check_run_id},
            )

    def apply_and_approve(self, check_run_id: int) -> bool:
        """Returns True in case of no error & False otherwise"""
        try:
            LOGGER.info("[tag:WER365AA10] Clicking on Navbar Approve & New button")
            hover_over_element(self.driver, self._get_navbar_approve_menu())
            explicit_wait_till_visibility(
                self.driver,
                self._get_navbar_approve_menu_approve_new_item(),
                TIMEOUT,
                msg="NavBar Approve Menu -> Approve New Item",
            )
            LOGGER.info("[tag:WER365AA20] Clicking on NavBar Approve button")
            self._get_navbar_approve_menu_approve_new_item().click()
            explicit_wait_till_visibility(
                self.driver,
                self._get_checking_account_dropdown_arrow(),
                TIMEOUT,
                msg="Checking Account DropDown Arrow",
            )
            # explicit_wait_till_visibility(self.driver, self._get_toast_message(), TIMEOUT, msg='Toast Message')
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.exception(
                f"[tag:WER365AA30] Probably check_run_id: {check_run_id} is processed. Please verify in r365 - {exc}"
            )
            # TODO: what does this except block mean?
            raise


class R365Runner(AccountingPaymentUpdateInterface):
    """Runner Class for R365"""

    def __init__(self, *args, **kwargs):
        kwargs["is_angular"] = True
        super().__init__(*args, **kwargs)
        self.login_page = R365LoginPage(self.driver)
        self.home_page = R365HomePage(self.driver)
        self.payment_page = R365ManualPaymentPage(self.driver)

    def _login(self):
        base_url = self.run.job.login_url
        get_url(self.driver, base_url)

        self.login_page.login(self.run.job.username, self.run.job.password)
        explicit_wait_till_visibility(
            self.driver,
            self.home_page.get_navbar_vendor_menu(),
            msg="NavBar Vendor Menu",
        )
        self.home_page.check_popup()
        explicit_wait_till_visibility(
            self.driver,
            self.home_page.get_navbar_vendor_menu(),
            TIMEOUT,
            msg="Navbar Vendor Menu",
        )

    def _update_payment_records(self, run: Run) -> List[CheckRun]:
        """TODO: Implement Check Run logic"""
        LOGGER.info(f"[tag:RUPR][run:{run.id}] Updating Payment Record for {run}")
        check_runs = []
        for key, value in run.request_parameters["accounting"].items():
            value = _update_request_parameters(run, value)
            check_run_id = value["chequerun_id"]
            LOGGER.debug(
                f"[tag:RUPR][run:{run.id}] Updating payment record for Payment {key} : {value}"
            )

            try:
                check_run = CheckRun.create_unique(self.run, check_run_id)
            except CheckRunExists as exc:
                if not exc.previous_checkrun.is_patch_success:
                    # if it was successful, but the patch hasn't finished, add it to the list of checkruns for
                    # which we'll notify Core API of success
                    check_runs.append(exc.previous_checkrun)
                # do not proceed further for duplicates
                continue

            except CheckRunDisabled as exc:
                LOGGER.debug(f"[tag:RUPR][run:{run.id}] {str(exc)}")
                continue

            try:
                self._update_payment_record(run=run, value=value)
                check_run.record_export_success()
            except ContextualError as exc:
                check_run.record_export_failure(exc)
                settings.PIQ_CORE_CLIENT.post_billpay_cheque_error(
                    check_run_id, exc.message
                )

            check_runs.append(check_run)
        return check_runs

    def _update_payment_record(self, run: Run, value: dict):
        self.home_page.go_to_manual_payment_page(run=run)
        self.payment_page.fill_manual_payment_form(value)
        self.payment_page.validate_manual_payment(
            value["chequerun_id"], value["payment_total"]
        )

        if not settings.LOCAL_ENV:
            self.payment_page.apply_and_approve(value["chequerun_id"])

    def start_payment_update_flow(self, run: Run) -> List[CheckRun]:
        """
        Initiates the Payment Update Workflow
        :param run: Run Object
        :return: Returns the list of Check Runs
        """
        check_runs = []
        try:
            self._login()
            check_runs += self._update_payment_records(run)
        finally:
            self._quit_driver()

        return check_runs

    def login_flow(self, run: Run) -> bool:
        self._login()


def _update_request_parameters(run: Run, value: dict):
    fields = [
        ("location_id", Location),
        ("vendor_id", Vendor),
        ("bank_account", BankAccount),
    ]

    for (key, coreobject_cls) in fields:
        data = value[key].lower()
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
            value[key] = mapping["mapped_to"]

    return value
