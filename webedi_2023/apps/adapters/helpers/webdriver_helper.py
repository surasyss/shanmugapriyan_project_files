import os
import time

# pylint: disable=no-name-in-module
from pytractor.webdriver import Chrome
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    JavascriptException,
    TimeoutException,
    StaleElementReferenceException,
    ElementClickInterceptedException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait
from spices.django3.conf import LOCAL_ENV
from webdriver_manager.chrome import ChromeDriverManager

from apps.adapters.helpers import LOGGER
from apps.adapters.helpers.helper import sleep
from integrator.conf import DRIVER_EXECUTABLE_PATH
from integrator.settings import BASE_DIR, PROXY_SERVER

IGNORED_EXCEPTIONS = [NoSuchElementException]
WEB_DRIVER_EXCEPTIONS = (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    ElementClickInterceptedException,
)


class DriverFactory:
    """WebDriver factory"""

    user_agent = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"
    )

    @staticmethod
    def new(
        download_location: str,
        headless: bool = True,
        is_angular: bool = False,
        uses_proxy: bool = False,
        user_agent: str = user_agent,
    ) -> WebDriver:
        """
        Create and return the webdriver
        :param download_location: Files download location for the browser
        :param headless: Boolean parameter to enable/disable headless mode
        :param is_angular: Boolean parameter for Angular/non-angular sites
        :param uses_proxy: Boolean parameter for using proxy or not
        :param user_agent: Str parameter for specifying user agent
        :return: Returns the WebDriver
        """
        LOGGER.info("Creating new Chrome WebDriver...")

        # parse parameters
        height = 1280
        width = 1300
        driver_implicit_wait = 15

        LOGGER.info(f" - Window Height: {height}, Window Width: {width}")
        LOGGER.info(f" - Headless: {headless}")
        LOGGER.info(f" - Angular: {is_angular}")
        LOGGER.info(f" - Using Proxy: {uses_proxy}")
        LOGGER.info(f" - Download Location: {download_location}")
        LOGGER.info(f" - Driver Implicit wait: {driver_implicit_wait}")

        # prepare options
        headless = bool(os.getenv("DRIVER_HEADLESS", "True").lower() == "true")
        options = DriverFactory._prepare_driver_options(
            download_location=download_location,
            headless=headless,
            uses_proxy=uses_proxy,
            user_agent=user_agent,
        )
        driver_executable_path = DriverFactory._get_chrome_executable_path()

        # build and configure driver
        if is_angular:
            driver = Chrome(
                executable_path=driver_executable_path,
                options=options,
                script_timeout=100,
                test_timeout=100,
            )
        else:
            driver = webdriver.Chrome(
                executable_path=driver_executable_path, options=options
            )

        if headless:
            DriverFactory._enable_download_in_headless_chrome(driver, download_location)

        driver.set_window_size(width, height)
        driver.implicitly_wait(driver_implicit_wait)

        # Remove navigator.webdriver Flag using JavaScript
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            """
            },
        )
        # Remove navigator.plugins Flag using JavaScript
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                })
            """
            },
        )
        return driver

    @staticmethod
    def _get_chrome_executable_path():
        return (
            ChromeDriverManager(path="/tmp/").install()
            if LOCAL_ENV
            else DRIVER_EXECUTABLE_PATH
        )

    @staticmethod
    def _prepare_driver_options(
        download_location: str, headless: bool, uses_proxy: bool, user_agent: str
    ) -> Options:
        """
        The following code enables file downloading in headless chrome
        """
        LOGGER.info("Preparing options")
        opts = Options()
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")  # Adding this to prevent tab crash
        opts.add_argument("--allow-running-insecure-content")
        opts.add_argument("--ignore-certificate-errors")
        opts.add_argument(f"user-agent={user_agent}")
        opts.add_argument("--kiosk-printing")
        opts.set_capability("acceptInsecureCerts", True)

        if uses_proxy:
            opts.add_argument(f"--proxy-server={PROXY_SERVER}")

        if headless:
            LOGGER.info("Setting headless = True")
            opts.add_argument("--headless")
            # opts.add_argument("--headless=new")

        if download_location:
            LOGGER.info("Setting preferences...")
            os.makedirs(download_location, exist_ok=True)
            preferences = {
                "download.default_directory": download_location,
                "profile.default_content_setting_values.automatic_downloads": 1,
                "browser.download.manager.showWhenStarting": False,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,
                "safebrowsing.disable_download_protection": True,
                "plugins.always_open_pdf_externally": True,
                "plugins.plugins_disabled": ["Chrome PDF Viewer"],
            }
            opts.add_experimental_option("prefs", preferences)
        return opts

    @staticmethod
    def _enable_download_in_headless_chrome(driver: WebDriver, download_location: str):
        """
        The following code enables file downloading in headless chrome
        """
        LOGGER.info("Enabling download in headless chrome")
        command = ("POST", "/session/$sessionId/chromium/send_command")
        # noinspection PyProtectedMember
        driver.command_executor._commands[  # pylint: disable=protected-access
            "send_command"
        ] = command
        params = {
            "cmd": "Page.setDownloadBehavior",
            "params": {"behavior": "allow", "downloadPath": download_location},
        }
        command_result = driver.execute("send_command", params)
        LOGGER.info("response from browser:")
        for key in command_result:
            LOGGER.info(f"result:{key}: {command_result[key]}")


def get_url(driver: WebDriver, url: str, retry_attempts: int = 5):
    for index in range(retry_attempts):
        try:
            LOGGER.info(f"{index}. Navigating to {url}")
            driver.get(url)
            break
        except Exception as excep:  # pylint: disable=broad-except
            LOGGER.warning(f"{index}. Some error while opening url: {url} - {excep}")
            sleep(2, msg="Retry url")


def set_implicit_timeout(driver: WebDriver, timeout: int):
    LOGGER.info(f"Setting implicit timeout: {timeout}")
    driver.implicitly_wait(timeout)


def explicit_wait_till_visibility(
    driver, element, timeout: int = 20, msg: str = None, ignored_exceptions=None
):
    """
    Waits explicitly for an element to be visible
    :param driver: WebDriver
    :param element: WebElement
    :param timeout: Customer timeout in secs default: 20
    :param msg: Str Any message while waiting for the element
    :param ignored_exceptions: List of Exceptions to be ignored
    :return:
    """
    LOGGER.info(
        f"Explicitly waiting upto {timeout} seconds for the element to be visible. {msg}"
    )
    return WebDriverWait(driver, timeout, ignored_exceptions=ignored_exceptions).until(
        EC.visibility_of(element)
    )


def explicit_wait_till_invisibility(
    driver, element, timeout: int = 20, msg: str = None, ignored_exceptions=None
):
    """
    Waits expicitly for an element to be invisible
    :param driver: WebDriver
    :param element: WebElement
    :param timeout: Custom timeout in secs default: 20
    :param msg: Str Any message while waiting for the element
    :param ignored_exceptions: List of Exceptions to be ignored
    :return:
    """
    LOGGER.info(
        f"Explicitly waiting upto {timeout} seconds for the element to be invisible. {msg}"
    )
    return WebDriverWait(driver, timeout, ignored_exceptions=ignored_exceptions).until(
        EC.invisibility_of_element(element)
    )


def explicit_wait_till_clickable(
    driver, locator, timeout: int = 20, msg: str = None, ignored_exceptions=None
):
    """
    Waits explicitly for an element to be clickable
    :param ignored_exceptions: List of Exceptions to be ignored
    :param msg: Str Any message while waiting for the element
    :param timeout: Customer timeout in secs default: 20
    :param driver: WebDriver
    :param locator: WebElement Locator
    :return:
    """
    LOGGER.info(
        f"Explicitly waiting upto {timeout} seconds for the element to be clickable. {msg}"
    )
    return WebDriverWait(driver, timeout, ignored_exceptions=ignored_exceptions).until(
        EC.element_to_be_clickable(locator)
    )


def explicit_wait_till_url_changes(driver, url: str, timeout: int = 20):
    """
    Waits explicitly for the URL to be changed to the expected URL
    :param driver: WebDriver
    :param url: Expected URL
    :param timeout: timeout in secs
    :return:
    """
    LOGGER.info(
        f"Explicitly waiting upto {timeout} secs for URl to be changed to {url}"
    )
    return WebDriverWait(driver, timeout).until(EC.url_changes(url))


def explicit_wait_till_url_to_be(driver, url: str, timeout: int = 20):
    """
    Waits explicitly for the URL to be the expected URL
    :param driver: WebDriver
    :param url: Expected URL
    :param timeout: timeout in secs
    :return:
    """
    LOGGER.info(
        f"Explicitly waiting upto {timeout} secs for URl to be changed to {url}"
    )
    return WebDriverWait(driver, timeout).until(EC.url_to_be(url))


def explicit_wait_till_url_contains(driver, partial_url: str, timeout: int = 20):
    """
    Waits explicitly for the URL to be the expected URL
    :param driver: WebDriver
    :param partial_url: Expected URL
    :param timeout: timeout in secs
    :return:
    """
    LOGGER.info(f"Explicitly waiting for {timeout} secs for URl contains {partial_url}")
    return WebDriverWait(driver, timeout).until(EC.url_contains(partial_url))


def explicit_wait_for_frame(
    driver, locator, timeout: int = 20, msg: str = None, ignored_exceptions=None
):
    """
    Waits explicitly for a frame to be available
    :param driver: WebDriver
    :param locator: Locator
    :param timeout: Customer timeout in secs default: 20
    :param msg: Str Any message while waiting for the element
    :param ignored_exceptions: List of Exceptions to be ignored
    :return:
    """
    LOGGER.info(
        f"Explicitly waiting upto {timeout} seconds for the frame to be available. {msg}"
    )
    return WebDriverWait(driver, timeout, ignored_exceptions=ignored_exceptions).until(
        EC.frame_to_be_available_and_switch_to_it(locator)
    )


def wait_for_loaders(
    driver, by_selector=By.CSS_SELECTOR, value=None, timeout=20, retry_attempts=5
):
    """
    Wait for loaders, especially loaders loading multiple times
    :param driver:
    :param by_selector:
    :param value:
    :param timeout:
    :param retry_attempts:
    :return:
    """
    try:
        if not value:
            raise ValueError(f"Both web_element and locator value can't be none")

        set_implicit_timeout(driver, 5)
        for index in range(retry_attempts):
            if value:
                explicit_wait_till_visibility(
                    driver,
                    driver.find_element(by_selector, value),
                    timeout,
                    msg=f"Loader.. {index}",
                )
                explicit_wait_till_invisibility(
                    driver,
                    driver.find_element(by_selector, value),
                    timeout,
                    msg=f"Loader.. {index}",
                )
    except WEB_DRIVER_EXCEPTIONS as excep:
        LOGGER.warning(f"Skipping Loader check! {excep}")
    finally:
        set_implicit_timeout(driver, 15)


def wait_for_element(
    driver,
    by_selector=By.CSS_SELECTOR,
    value=None,
    timeout=20,
    msg=None,
    retry_attempts=5,
    raise_exception=True,
):
    """
    Wait for an web element visibility & retries on exception
    :param driver:
    :param by_selector:
    :param value:
    :param timeout:
    :param msg:
    :param retry_attempts:
    :param raise_exception:
    :return:
    """
    wd_exception = None
    for index in range(retry_attempts):
        try:
            if not value:
                raise ValueError(f"value can't be none")

            if value:
                explicit_wait_till_visibility(
                    driver,
                    driver.find_element(by_selector, value),
                    timeout=timeout,
                    msg=msg,
                )
            LOGGER.info(f"{index}. Web Element found - [{msg}]")
            wd_exception = None
            break
        except WEB_DRIVER_EXCEPTIONS as excep:
            wd_exception = excep
            LOGGER.info(f"Web Element not found - Retry attempt: {index} - [{msg}]")
    if raise_exception and wd_exception:
        raise WebDriverException(f"WebElement not found - {wd_exception}")


def wait_for_ajax(driver: WebDriver, timeout: int = 20, msg: str = None):
    LOGGER.info(f"Waiting for ajax call to complete: {msg}")
    return WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return jQuery != undefined && jQuery.active == 0")
    )


def scroll_down(driver):
    """
    Scrolls down to the end of the page
    :param driver: WebDriver
    :return: Nothing
    """
    LOGGER.info("Scrolling down to the end of the page.")
    len_of_page = driver.execute_script(
        "window.scrollTo(0, document.body.scrollHeight);"
        "var lenOfPage=document.body.scrollHeight;return lenOfPage;"
    )
    match = False
    while match is False:
        last_count = len_of_page
        time.sleep(3)
        len_of_page = driver.execute_script(
            "window.scrollTo(0, document.body.scrollHeight);"
            "var lenOfPage=document.body.scrollHeight;return lenOfPage;"
        )
        if last_count == len_of_page:
            match = True


def is_element_present(driver, element) -> bool:
    """
    Checks if the element is present in the DOM
    :param driver: WebDriver
    :param element: WebElement to be checked for the presence
    :return: Returns boolean True in case the Element is present in DOM
    """
    driver.implicitly_wait(0)
    result = False
    if element:
        result = True
    LOGGER.info("Checking if the element is present. Returning %s", str(result))
    return result


def get_current_window_handle(driver):
    """
    Returns the current window handle
    :param driver: WebDriver
    :return: Main window handle
    """
    main_window = driver.current_window_handle
    LOGGER.info("Main window: %s", main_window)
    return main_window


def select_dropdown_option(elem, index=None, value=None, text=None):
    """
    Select option from Dropdown
    :param elem: Dropdown WebElement
    :param index: The value to be selected from the dropdown
    :param value: The value to be selected from the dropdown
    :param text: The value to be selected from the dropdown
    :return: nothing
    """
    if not (index or value or text):
        raise ValueError(f"All [index, value, text] can't be None")

    LOGGER.info(
        f"Selecting dropdown option index: {index}, value: {value}, text: {text}"
    )
    select = Select(elem)

    if index:
        select.select_by_index(index=index)
    if value:
        select.select_by_value(value=value)
    if text:
        select.select_by_visible_text(text=text)


def select_dropdown_option_by_value(elem, value):
    """
    Select option from Dropdown by value
    :param elem: Dropdown WebElement
    :param value: The value to be selected from the dropdown
    :return: nothing
    """
    LOGGER.info("Selecting the option %s from the dropdown.", value)
    select = Select(elem)
    select.select_by_value(value)


def select_dropdown_option_by_visible_text(elem, text):
    """
    Select option from Dropdown by visible text
    :param elem: Dropdown WebElement
    :param text: The text to be selected from the dropdown
    :return: nothing
    """
    LOGGER.info("Selecting the option %s from the dropdown.", text)
    select = Select(elem)
    select.select_by_visible_text(text)


def find_element_in_list_by_text(element_list: list, text: str):
    """
    Finds the webElement from the list of webElements with the given text
    :param element_list: List of WebElements
    :param text: Text to be searched in the webelement list
    :return: Returns the web element
    """
    LOGGER.info('Finding "%s" text in the list of webElements', text)
    for elem in element_list:
        if elem.text.upper() == text.upper():
            LOGGER.info('Found "%s" in the list of webElements', text)
            return elem
    return None


def find_element_in_list_by_substring(
    element_list: list, text: str, split_char: str, index: int
) -> WebElement:
    """
    This is specific to R365 only
    Finds the webElement from the list of webElements with the given text
    :param element_list: List of WebElements
    :param text: Text to be searched in the webelement list
    :param split_char: character by which string to be split
    :param index: index count for the splitted substring
    :return: Returns the web element
    """
    LOGGER.info('Finding "%s" text in the list of webElements', text)
    for elem in element_list:
        if elem.text.rsplit(split_char)[index].upper().strip() == text.upper().strip():
            LOGGER.info('Found "%s" in the list of webElements', text)
            return elem
    return None


def take_screenshot(driver, filename):
    filename = os.path.join(BASE_DIR, "apps/adapters/screenshots/" + filename)
    LOGGER.info(f"Taking screenshot & storing at: {filename}")
    driver.save_screenshot(filename)


def scroll_down_to_element(driver, element):
    try:
        driver.execute_script("arguments[0].scrollIntoView();", element)
    except JavascriptException:
        LOGGER.error("Error scrolling down web element!")
    except NoSuchElementException:
        LOGGER.error("Element not found!")


def hover_over_element(driver, element):
    hover = ActionChains(driver).move_to_element(element)
    hover.perform()


def handle_popup(
    driver,
    by_selector=By.CSS_SELECTOR,
    value=None,
    timeout=10,
    msg="Pop up",
    retry_attempts=5,
):
    """
    Handles single/multiple pop-ups
    :param driver:
    :param by_selector:
    :param value:
    :param timeout:
    :param msg:
    :param retry_attempts:
    :return:
    """
    try:
        LOGGER.info(f"Checking Popup Loop")
        for index in range(retry_attempts):
            set_implicit_timeout(driver, 5)
            popup_element = driver.find_element(by_selector, value)
            explicit_wait_till_visibility(
                driver, popup_element, timeout=timeout, msg=msg
            )
            popup_element.click()
            LOGGER.info(f"{index}. Popup found & closed - {msg}")
    except WEB_DRIVER_EXCEPTIONS:
        LOGGER.info(f"{index}. Popup not found - {msg}")
    finally:
        set_implicit_timeout(driver, 15)


def has_invoices(
    driver,
    by_selector=By.CSS_SELECTOR,
    value=None,
    msg: str = "Invoice table",
    retry_attempts=1,
) -> bool:
    """
    Returns True if invoices are present else False
    :param driver:
    :param by_selector:
    :param value:
    :param msg:
    :param retry_attempts:
    :return:
    """
    try:
        wait_for_element(
            driver,
            by_selector=by_selector,
            value=value,
            msg=msg,
            retry_attempts=retry_attempts,
        )
        LOGGER.info(f"Invoices found")
        return True
    except WebDriverException:
        LOGGER.info(f"No Invoice found")
        return False


def execute_script_click(driver, element: WebElement):
    """
    Click through script
    """
    LOGGER.info(f"Clicking on {element.text}")
    driver.execute_script("arguments[0].click();", element)


def close_extra_handles(driver):
    """
    Close Chrome handles except main handle
    """
    handles = driver.window_handles
    main_handle = driver.window_handles[0]
    LOGGER.info(f"Driver Handles found: {handles}")
    handles.remove(main_handle)

    for handle in handles:
        LOGGER.info(f"Closing handle: {handle}")
        driver.switch_to_window(handle)
        driver.close()
    driver.switch_to_window(main_handle)


# noinspection PyPep8Naming,PyProtectedMember
class visibility_of_nth_element_located:  # pylint: disable=invalid-name
    """An expectation for checking that a specific element from a list is present on the DOM of a
    page and visible. Visibility means that the element is not only displayed
    but also has a height and width that is greater than 0.
    locator - used to find the element
    returns the WebElement once it is located and visible
    """

    def __init__(self, locator, index: int):
        self.locator = locator
        if not isinstance(index, int):
            raise TypeError(f"Index must be integer, received value {index}")
        self.index = index

    def __call__(self, driver):
        count = None
        try:
            elements = EC._find_elements(driver, self.locator)
            count = len(elements)
            return EC._element_if_visible(elements[self.index])
        except IndexError:
            if count:
                LOGGER.warning(
                    f"[visibility_of_nth_element_located] "
                    f"Tried accessing element index {self.index}, but only {count} elements were found"
                )
            raise
        except StaleElementReferenceException:
            return False
