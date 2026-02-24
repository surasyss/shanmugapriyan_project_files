import json
import os
from datetime import datetime, date
from typing import List
from retry.api import retry

from selenium.common.exceptions import NoSuchElementException, WebDriverException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from apps.adapters.base import VendorDocumentDownloadInterface, PasswordBasedLoginPage
from apps.adapters.framework import download
from apps.adapters.helpers.webdriver_helper import (
    set_implicit_timeout,
    get_url,
    wait_for_element,
    handle_popup,
    execute_script_click,
)
from apps.adapters.vendors import LOGGER
from apps.runs.models import Run, DiscoveredFile, DocumentType, FileFormat
from spices.datetime_utils import date_from_string

LOGIN_PAGE_SELECTOR = {
    "LOGIN_LINK": "openLogin",
    "ACCEPT_COOKIES": "#onetrust-accept-btn-handler",
}

VERIFY_PAGE_SELECTOR = {"CONTINUE_BUTTON": 'input[value="Continue"]'}

HOME_PAGE_SELECTORS = {
    "RECEIPT_MANAGE_LINK": 'div.account a[href="/account/receiptmanager/"]',
    "USER_ICON": "a.header-user-icon.header-account",
    "LOGOUT_LINK": 'a[href="/account/signout/"]',
    "POP_UP_DIALOGUE": "fsrInvite",
    "POP_UP_CLOSE_BTN": "fsrFocusFirst",
}

MEMBER_PAGE_SELECTORS = {
    "MEMBER_ID_TEXTS": 'input[name="loyaltyCardNumber"]',
    "CONTINUE_BUTTON": 'input[value="Continue"]',
}

INVOICE_PAGE_SELECTORS = {
    "ALL_RADIO_BUTTON": 'input[id="_pageSize_All"]',
    "INVOICE_TABLE": "table table table",
}

INVOICE_DETAIL_PAGE_SELECTORS = {
    "NAVIGATOR_BAR": 'div[id="navigator"]',
    "STORE_DETAIL_TABLE": "table table table>tbody",
    "ITEM_DETAILS_TABLE": "table table table table>tbody",
    "MEMBER_DETAILS_TABLE": "table table table table table>tbody tr.bodytext",
}


class SmartFoodServiceLoginPage(PasswordBasedLoginPage):
    """Login page which uses a username / password combination to log a user in"""

    SELECTOR_USERNAME_TEXTBOX = 'div.signinForm input[id="un"]'
    SELECTOR_PASSWORD_TEXTBOX = 'div.signinForm input[id="pw"]'
    SELECTOR_LOGIN_BUTTON = 'div.signinForm input[value="Sign In"]'
    SELECTOR_ERROR_MESSAGE_TEXT = 'div[id="layBody"] p[class="failure"]'

    def get_login_link(self) -> WebElement:
        return self.driver.find_element_by_id(LOGIN_PAGE_SELECTOR["LOGIN_LINK"])


class SmartFoodServiceVerifyPage:
    def __init__(self, driver: WebDriver):
        self.driver = driver

    def get_continue_btn(self):
        return self.driver.find_element_by_css_selector(
            VERIFY_PAGE_SELECTOR["CONTINUE_BUTTON"]
        )


class SmartFoodServiceHomePage:
    def __init__(self, driver: WebDriver):
        self.driver = driver

    def get_receipt_manager_link(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_SELECTORS["RECEIPT_MANAGE_LINK"]
        )

    def get_user_icon(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_SELECTORS["USER_ICON"]
        )

    def get_logout_link(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            HOME_PAGE_SELECTORS["LOGOUT_LINK"]
        )

    def get_pop_up_dialogue(self) -> WebElement:
        return self.driver.find_element_by_id(HOME_PAGE_SELECTORS["POP_UP_DIALOGUE"])

    def get_pop_up_close_btn(self) -> WebElement:
        return self.driver.find_element_by_id(HOME_PAGE_SELECTORS["POP_UP_CLOSE_BTN"])


class SmartFoodServiceMemberPage:
    def __init__(self, driver: WebDriver):
        self.driver = driver

    def get_member_id_texts(self) -> List[WebElement]:
        return self.driver.find_elements_by_css_selector(
            MEMBER_PAGE_SELECTORS["MEMBER_ID_TEXTS"]
        )

    def get_continue_button(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            MEMBER_PAGE_SELECTORS["CONTINUE_BUTTON"]
        )


class SmartFoodServiceInvoicePage:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.vendor_name = "Smart Food Service"

    def get_all_radio_button(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            INVOICE_PAGE_SELECTORS["ALL_RADIO_BUTTON"]
        )

    def get_invoice_table_rows(self) -> List[WebElement]:
        return self.driver.find_elements_by_css_selector(
            INVOICE_PAGE_SELECTORS["INVOICE_TABLE"]
        )[6].find_elements_by_tag_name("tr")

    def get_invoice_table_data(self, run: Run, from_date: date) -> List[DiscoveredFile]:
        discovered_files = []
        invoice_links_list = []

        rows = self.get_invoice_table_rows()
        for row in rows[1:]:
            if row.text == "Your search returned no results.":
                return discovered_files

            invoice_date_element = row.find_elements_by_tag_name("td")[
                0
            ].find_element_by_tag_name("a")
            invoice_date_text = invoice_date_element.text.strip()

            if (
                invoice_date_text == "Your search returned no results."
            ):  # Sometimes there are no records
                return discovered_files

            invoice_date = date_from_string(invoice_date_text, "%m/%d/%Y %H:%M %p")
            if invoice_date < from_date:
                return discovered_files

            invoice_link = invoice_date_element.get_attribute("href")
            invoice_number = invoice_link.split("=")[1]
            reference_code = f"{invoice_number}"

            if invoice_link in invoice_links_list:
                continue

            invoice_links_list.append(invoice_link)

            location = row.find_elements_by_tag_name("td")[1].text
            document_properties = {
                "customer_number": None,
                "invoice_number": invoice_number,
                "invoice_date": str(invoice_date),
                "total_amount": row.find_elements_by_tag_name("td")[3].text,
                "vendor_name": self.vendor_name,
                "restaurant_name": location,
                "store_location": location,
            }
            try:
                # pylint: disable=no-member
                discovered_file = DiscoveredFile.build_unique(
                    run,
                    reference_code,
                    document_type=DocumentType.INVOICE.ident,
                    file_format=FileFormat.JSON.ident,
                    original_download_url=invoice_link,
                    original_filename=f"{reference_code}.json",
                    document_properties=document_properties,
                )
            except DiscoveredFile.AlreadyExists:
                LOGGER.info(
                    f"Discovered file already exists with reference code : {reference_code}"
                )
                continue  # skip if seen before
            discovered_files.append(discovered_file)
            LOGGER.info(
                "Invoice details row data: %s", str(discovered_file.document_properties)
            )

        return discovered_files


class SmartFoodServiceInvoiceDetailPage:
    def __init__(self, driver: WebDriver, download_location: str):
        self.driver = driver
        self.download_location = download_location

    def get_navigator_bar(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            INVOICE_DETAIL_PAGE_SELECTORS["NAVIGATOR_BAR"]
        )

    def get_invoice_tables(self) -> List[WebElement]:
        return self.driver.find_elements_by_css_selector(
            INVOICE_DETAIL_PAGE_SELECTORS["STORE_DETAIL_TABLE"]
        )

    def get_item_details_table(self) -> WebElement:
        return self.driver.find_elements_by_css_selector(
            INVOICE_DETAIL_PAGE_SELECTORS["ITEM_DETAILS_TABLE"]
        )[0]

    def get_member_details_table(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            INVOICE_DETAIL_PAGE_SELECTORS["MEMBER_DETAILS_TABLE"]
        )

    def get_store_details(self) -> WebElement:
        return (
            self.get_invoice_tables()[0]
            .find_elements_by_css_selector("tr")[1]
            .find_element_by_css_selector("td")
        )

    def is_actual_line_item(self, row: WebElement) -> bool:
        set_implicit_timeout(self.driver, 0.1)

        if row.find_element_by_css_selector("table tbody img") and row.text != "":
            set_implicit_timeout(self.driver, 15)
            return True

        return False

    def get_item_details(self) -> List:
        item_details = []
        rows = self.get_item_details_table().find_elements_by_tag_name("tr")

        if rows[0].text != "Link Type Qty Description Item # Price Ext. Price  ":
            raise Exception(f"Item Details table not found!")

        LOGGER.info(f"Fetching Item Details.")
        for row in rows[1:]:
            try:
                item = {}
                if self.is_actual_line_item(row):
                    cells = row.find_elements_by_css_selector("td")
                    item["quantity"] = cells[4].text.split(" ")[0]
                    item["unit"] = (
                        cells[4].text.split(" ")[1]
                        if len(cells[4].text.split(" ")) == 2
                        else None
                    )
                    item["description"] = cells[5].text
                    item["item_number"] = cells[6].text
                    item["unit_price"] = cells[7].text
                    item["ext_price"] = cells[8].text
                    # Passing False always since tax per item is not available. In case tax per line item is available
                    # then pass is_taxable=True
                    # previously used logic: bool('T' in cells[9].text.upper())
                    item["is_taxable"] = False

                    item_details.append(item)
                    LOGGER.info(f"Item Details found: {item}")
            except NoSuchElementException:
                set_implicit_timeout(self.driver, 15)

        return item_details

    def get_member_id(self) -> str:
        try:
            LOGGER.info(f"Fetching Member Details.")
            set_implicit_timeout(self.driver, 0.5)
            row = (
                self.get_member_details_table()
                .find_element_by_xpath("..")
                .find_elements_by_tag_name("tr")[1]
            )
            member_id = row.find_elements_by_tag_name("td")[1].text
            LOGGER.info(f"Member Details found: {member_id}")
            return member_id
        except NoSuchElementException:
            LOGGER.info(f"Member Details not found!")
            return None
        finally:
            set_implicit_timeout(self.driver, 15)

    def create_invoice_file(
        self, discovered_file: DiscoveredFile, item_details: List, customer_id: str
    ):
        invoice_data = {
            "version": 1,
            "meta": {
                "generator": {
                    "code": f"webedi.{SmartFoodServiceRunner.__name__}",
                    "execution_id": f"webedi-connector_{discovered_file.connector_id}-"
                    f"job_{discovered_file.run.job_id}-"
                    f"run_{discovered_file.run_id}",
                }
            },
            "invoices": [],
        }

        invoice = {
            "invoice_date": discovered_file.document_properties["invoice_date"],
            "invoice_number": discovered_file.document_properties["invoice_number"],
            "total_amount": discovered_file.document_properties["total_amount"],
            "tax_amount": None,
            "invoice_type": "debit",
            "customer_number": customer_id,
            "customer_name": discovered_file.document_properties["restaurant_name"],
            "lineitems": [],
        }

        for item in item_details:
            line_item = {
                "extension": item["ext_price"],
                "manufacturer_number": None,
                "manufacturer_name": None,
                "quantity_ordered": item["quantity"],
                "quantity_delivered": item["quantity"],
                "unit_discount": None,
                "unit_deposit": None,
                "unit_price": item["unit_price"],
                "item_sku": item["item_number"],
                "item_name": item["description"],
                "is_taxable": item["is_taxable"],
                "pack_size": None,
                "unit": item["unit"],
                "is_split_case": None,
            }
            invoice["lineitems"].append(line_item)

        invoice_data["invoices"].append(invoice)

        file_path = os.path.join(
            self.download_location, discovered_file.original_filename
        )
        with open(file_path, "w") as invoice_file:
            json.dump(invoice_data, invoice_file)

        _downloader = download.NoOpDownloader(local_filepath=file_path)
        download.download_discovered_file(discovered_file, _downloader)

    def fetch_invoice_details(self, discovered_files: List[DiscoveredFile]):
        for discovered_file in discovered_files:
            LOGGER.info(f"Navigating to {discovered_file.original_download_url}")
            self.driver.get(discovered_file.original_download_url)
            wait_for_element(
                self.driver,
                value=INVOICE_DETAIL_PAGE_SELECTORS["NAVIGATOR_BAR"],
                msg="Navigation Bar",
            )

            item_details = self.get_item_details()
            customer_id = self.get_member_id()
            self.create_invoice_file(discovered_file, item_details, customer_id)


class SmartFoodServiceRunner(VendorDocumentDownloadInterface):
    """Runner Class for Smart Food Service"""

    # uses_proxy = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.login_page = SmartFoodServiceLoginPage(self.driver)
        self.verify_page = SmartFoodServiceVerifyPage(self.driver)
        self.home_page = SmartFoodServiceHomePage(self.driver)
        self.member_page = SmartFoodServiceMemberPage(self.driver)
        self.invoice_page = SmartFoodServiceInvoicePage(self.driver)
        self.invoice_detail_page = SmartFoodServiceInvoiceDetailPage(
            self.driver, self.download_location
        )

    def get_cookies_button(self) -> WebElement:
        return self.driver.find_element_by_css_selector(
            LOGIN_PAGE_SELECTOR["ACCEPT_COOKIES"]
        )

    @retry(WebDriverException, tries=3, delay=2)
    def _login(self):
        """
        Login to Southern Wine Online
        :return: Nothing
        """
        login_url = "https://www.chefstore.com/account/signin/"
        get_url(self.driver, login_url)
        self.get_cookies_button().click()
        self.login_page.login(self.run.job.username, self.run.job.password)

    def _verify_login(self):
        try:
            if self.verify_page.get_continue_btn().is_displayed():
                LOGGER.info(f"Signing out from all devices")
                self.verify_page.get_continue_btn().click()
                wait_for_element(
                    self.driver,
                    value=HOME_PAGE_SELECTORS["RECEIPT_MANAGE_LINK"],
                    msg="Receipt Manager Link",
                    retry_attempts=1,
                    raise_exception=False,
                )
        except NoSuchElementException:
            LOGGER.info(f"Verify Login page is not found.")

    def get_save_button(self):
        return self.driver.find_elements(By.CSS_SELECTOR, "input[value='Save']")

    def confirm_account_details(self):
        for index in range(3):
            handle_popup(
                self.driver,
                by_selector=By.ID,
                value=HOME_PAGE_SELECTORS["POP_UP_CLOSE_BTN"],
                msg="Pop Up Dialogue",
                retry_attempts=1,
            )
            edit_account_url = "https://www.chefstore.com/account/edit/"
            save_button = self.get_save_button()
            if self.driver.current_url == edit_account_url and save_button:
                execute_script_click(self.driver, save_button[0])
                if self.get_save_button():
                    continue
            break

    def _logout(self):
        set_implicit_timeout(self.driver, 5)
        get_url(self.driver, "https://www.chefstore.com/account/")
        try:
            wait_for_element(
                self.driver,
                value=HOME_PAGE_SELECTORS["USER_ICON"],
                retry_attempts=1,
                msg="User Icon Link",
            )
            handle_popup(
                self.driver,
                by_selector=By.ID,
                value=HOME_PAGE_SELECTORS["POP_UP_CLOSE_BTN"],
                msg="Pop Up Dialogue",
            )
            self.home_page.get_user_icon().click()
            wait_for_element(
                self.driver,
                value=HOME_PAGE_SELECTORS["LOGOUT_LINK"],
                retry_attempts=1,
                msg="Logout Link",
            )
            self.home_page.get_logout_link().click()
        except WebDriverException as excep:
            LOGGER.info(f"Something went wrong while log out - {excep}")
        finally:
            set_implicit_timeout(self.driver, 15)

    def _got_to_receipt_manager(self):
        url = "https://www.chefstore.com/account/receiptmanager/"
        get_url(self.driver, url=url)

    def _check_for_member_page(self):
        self._got_to_receipt_manager()
        return self.member_page.get_member_id_texts()

    def _download_documents(self) -> List[DiscoveredFile]:
        """
        Chooses the documents to be downloaded based on the document type
        :return: Returns the list of Discovered Files
        """
        document_type = self.run.job.requested_document_type
        if document_type == "invoice":
            return self._download_invoices()

        raise NotImplementedError(
            f"Requested Document Type is not supported: {document_type}"
        )

    def _download_invoices(self) -> List[DiscoveredFile]:
        """
        Downloads the Invoices
        :return: Returns the list of the Discovered Files
        """
        LOGGER.info("Extracting data from table...")

        start_date = datetime.strptime(
            self.run.request_parameters["start_date"], "%Y-%m-%d"
        ).date()
        # Fetching all invoice table data
        discovered_files_list = self.invoice_page.get_invoice_table_data(
            self.run, start_date
        )

        LOGGER.info(
            f"Total Invoices within date range and download link available: {len(discovered_files_list)}"
        )
        # Download all the invoices
        self.invoice_detail_page.fetch_invoice_details(discovered_files_list)

        return discovered_files_list

    def view_receipts(self):
        get_url(
            self.driver, "https://www.chefstore.com/contact/receiptmanager/continue/"
        )

    def start_documents_download_flow(self, run: Run) -> List[DiscoveredFile]:
        """
        Initiates the Document Download Workflow
        :param run: Run Object
        :return: Returns the list of Discovered Files
        """
        discovered_files = []
        try:
            self._login()
            self._verify_login()
            self.confirm_account_details()
            members = self._check_for_member_page()

            if not members:
                self.view_receipts()
                wait_for_element(
                    self.driver,
                    value=INVOICE_PAGE_SELECTORS["ALL_RADIO_BUTTON"],
                    msg="All Radio Button",
                )
                discovered_files += self._download_documents()

            for index, member in enumerate(members):  # pylint: disable=unused-variable
                self.member_page.get_member_id_texts()[index].click()
                self.member_page.get_continue_button().click()
                self.view_receipts()

                wait_for_element(
                    self.driver,
                    value=INVOICE_PAGE_SELECTORS["ALL_RADIO_BUTTON"],
                    msg="All Radio Button",
                )
                discovered_files += self._download_documents()
                self._got_to_receipt_manager()
        finally:
            self._logout()
            self._quit_driver()

        return discovered_files

    def login_flow(self, run: Run):
        self._login()
