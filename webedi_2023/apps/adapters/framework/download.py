import base64
import os

import sentry_sdk
import textract
from django.db import IntegrityError
from django.db.models import Q
from retry import retry
from selenium.webdriver.ie.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from spices.ftp import get_random_file_from_ftp, move_file_from_ftp
from spices.services import ContextualError
from textract.exceptions import ExtensionNotSupported

from apps.adapters import LOGGER
from apps.adapters.helpers.helper import (
    wait_until_file_exists,
    rename_file,
    ZeroFileSizeException,
)
from apps.error_codes import ErrorCode
from apps.runs.models import DiscoveredFile


class BaseDownloader:
    """
    Interface for providing actual download logic when logged in to a site
    """

    def __init__(
        self,
        local_filepath: str,
        rename_to: str = None,
        file_exists_check_kwargs: dict = None,
        pre_download_action=None,
        post_download_action=None,
    ):
        super().__init__()
        self.file_exists_check_kwargs: dict = file_exists_check_kwargs or {}
        self.file_exists_check_kwargs.setdefault("timeout", 10)
        self.local_filepath = local_filepath
        self.rename_to = rename_to

        self._pre_download_action = pre_download_action or (lambda: None)
        self._post_download_action = post_download_action or (lambda: None)
        self._actual_downloaded_filepath = None
        self._final_local_filepath = None

    @retry(TimeoutError, tries=5, delay=1)
    def download(self):
        """
        Perform the downloads, and return the local file path to the downloaded file.
        :raises TimeoutError if download doesn't finish in specified/configured amount of time.
        """
        self._pre_download_action()
        self._perform_download_action()
        self._post_download_action()
        self._wait_for_download_completion()
        self._rename()
        return self._final_local_filepath

    def _perform_download_action(self):
        """Perform the download action"""
        raise NotImplementedError

    def _wait_for_download_completion(self):
        """Wait for file download to complete"""
        LOGGER.info("Checking if the file has been downloaded")
        self._actual_downloaded_filepath = wait_until_file_exists(
            self.local_filepath, **self.file_exists_check_kwargs
        )

    def _rename(self):
        """Optionally rename the downloaded file"""
        if self.rename_to:
            rename_file(self._actual_downloaded_filepath, self.rename_to)
            self._final_local_filepath = self.rename_to
        else:
            self._final_local_filepath = self._actual_downloaded_filepath


class NoOpDownloader(BaseDownloader):
    """Downloader implementation that does not actually download"""

    def _perform_download_action(self):
        """Do nothing"""

    def _wait_for_download_completion(self):
        """Wait for file download to complete"""
        self._actual_downloaded_filepath = self.local_filepath


class DriverBasedUrlGetDownloader(BaseDownloader):
    """
    Simple Selenium downloader implementation that downloads using a simple WebDriver.get(url), with built-in retries.
    Provides optional functionality to rename the downloaded file if desired.
    """

    def __init__(self, driver: WebDriver, download_url: str, **kwargs):
        super().__init__(**kwargs)
        self.driver = driver
        self.download_url = download_url

    def _perform_download_action(self):
        """Perform the download action"""
        LOGGER.info(f"Navigate to: {self.download_url}")
        self.driver.get(self.download_url)


class DriverExecuteScriptBasedDownloader(BaseDownloader):
    """
    Selenium downloader implementation that downloads using a simple WebDriver.execute_script(script),
    with built-in retries.
    Provides optional functionality to rename the downloaded file if desired.
    """

    def __init__(
        self, driver: WebDriver, script: str, script_args: tuple = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.driver = driver
        self.script = script
        self.script_args = script_args or ()

    def _perform_download_action(self):
        """Perform the download action"""
        self.driver.execute_script(self.script, *self.script_args)


class DriverExecuteCDPCmdBasedDownloader(BaseDownloader):
    """
    Selenium downloader implementation that downloads using a simple WebDriver.execute_cdp_cmd(script),
    with built-in retries.
    Provides optional functionality to rename the downloaded file if desired.
    """

    def __init__(self, driver: WebDriver, cmd: str, cmd_args: dict, **kwargs):
        super().__init__(**kwargs)
        self.driver = driver
        self.cmd = cmd
        self.cmd_args = cmd_args

    def _perform_download_action(self):
        """Perform the download action"""
        pdf_content = self.driver.execute_cdp_cmd(self.cmd, self.cmd_args)
        with open(self.local_filepath, "wb") as file:
            file.write(base64.b64decode(pdf_content["data"]))


class WebElementClickBasedDownloader(BaseDownloader):
    """
    Selenium downloader implementation that downloads usinby clicking a WebElement, with built-in retries.
    Provides optional functionality to rename the downloaded file if desired.
    """

    def __init__(self, element: WebElement, **kwargs):
        super().__init__(**kwargs)
        self.element = element

    def _perform_download_action(self):
        """Perform the download action"""
        self.element.click()


class FTPDownload(BaseDownloader):
    def __init__(self, local_filepath: str, credential):
        super().__init__(local_filepath=local_filepath)
        self.from_folder = credential.download_folder
        self.host = credential.server_address
        self.ftp_type = credential.ftp_type
        self.username = credential.username
        self.password = credential.password
        self.to_folder = credential.upload_folder

    def _wait_for_download_completion(self):
        pass

    def move_file_to_processed_folder(self, file_name):
        return move_file_from_ftp(
            file_name,
            self.from_folder,
            self.to_folder,
            self.host,
            username=self.username,
            password=self.password,
            ftp_type=self.ftp_type,
            append_timestamp=True,
        )

    def _perform_download_action(self):
        file_path = get_random_file_from_ftp(
            self.from_folder,
            self.host,
            username=self.username,
            password=self.password,
            ftp_type=self.ftp_type,
        )

        self._actual_downloaded_filepath = file_path


def download_discovered_file(
    discovered_file: DiscoveredFile, downloader: BaseDownloader
):
    base_log = f"[run:{discovered_file.run_id}]"
    LOGGER.info(f"[tag:INADFRDDF10]{base_log} Downloading discovered file")
    if discovered_file.pk:
        if not discovered_file.piq_container_id:
            # nothing to do here, this is a case of a discovered file that's updated it's run_id
            return

        raise ContextualError(
            code=ErrorCode.PE_INVALID_DISCOVERED_FILE.ident,  # pylint: disable=no-member
            message=ErrorCode.PE_INVALID_DISCOVERED_FILE.message,  # pylint: disable=no-member
        )
    try:
        discovered_file.local_filepath = downloader.download()
        LOGGER.info(
            f"[tag:INADFRDDF20]{base_log} File {discovered_file.original_filename}"
            f" successfully downloaded to {discovered_file.local_filepath}"
        )
        discovered_file.downloaded_successfully = True
        if os.stat(discovered_file.local_filepath).st_size == 0:
            raise ZeroFileSizeException

        # We have moved the de-duplication logic here instead of
        # df.build_unique() because we need the content hash to
        # identify duplicates. This method will raise exception
        # if we should not save the discovered_file to the DB
        _validate_against_existing_duplicate(discovered_file)

        discovered_file.save_content(
            discovered_file.local_filepath,
            compute_extracted_text_hash=discovered_file.run.job.connector.get_custom_properties.get(
                "compute_extracted_text_hash", True
            ),
        )

    except TimeoutError:
        LOGGER.warning(f"[tag:INADFRDDF40]{base_log} Download failed - timeout")
    except ZeroFileSizeException:
        LOGGER.warning(
            f"[tag:INADFRDDF41]{base_log} Downloaded file size is Zero - Hence skipping"
        )
    except IntegrityError:
        LOGGER.warning(
            f"[tag:INADFRDDF42]{base_log} Invoice is already downlaoded - Hence skipping"
        )
    except _DuplicateError as exc:
        LOGGER.info(f"Skipping creating DF: {exc}")
    except Exception as exc:
        LOGGER.exception(f"[tag:INADFRDDF50]{base_log} Download failed - {exc}")
        raise
    LOGGER.info(
        f"[tag:INADFRDDF60]{base_log} success={discovered_file.downloaded_successfully}"
    )


class _DuplicateError(Exception):
    pass


def _validate_against_existing_duplicate(new_df: DiscoveredFile):
    base_log = f"[run:{new_df.run_id}]"
    cont_hash, text_hash = DiscoveredFile.compute_hashes(new_df.local_filepath)
    if not cont_hash:
        LOGGER.warning(
            f"[tag:WAAFDFED10]{base_log} Started to looking for duplicates "
            f"for discovered file, but were unable to compute content_hash. "
            f"Skipping duplicate check."
        )
        return

    base_log = base_log + f"[ch:{cont_hash}]"
    LOGGER.info(
        f"[tag:WAAFDFED20]{base_log} Looking for duplicates for discovered "
        f"file (extracted_text_hash={text_hash})."
    )

    condition = Q(content_hash=cont_hash)
    if text_hash:
        condition = condition | Q(extracted_text_hash=text_hash)

    existing = (
        DiscoveredFile.objects.select_related("run", "run__job")
        .filter(condition)
        .first()
    )
    if not existing:
        LOGGER.debug(f"[tag:WAAFDFED30]{base_log} No duplicate found.")
        return

    if existing.run_id == new_df.run_id:
        LOGGER.warning(
            f"[tag:WAAFDFED40]{base_log} Found existing matching DF "
            f"{existing.id} whose run ({existing.run_id}) matches. "
            f"Possible (non-severe) bug in adapter code."
        )
        # no need to notify sentry in this case, this isn't critical

    if new_df.run.job.account_id != existing.run.job.account_id:
        msg = (
            f"CRITICAL: Found existing matching DF {existing.id} whose "
            f"account does not match new DF. Please investigate ASAP! "
            f"(old={existing.run.job.account_id},"
            f"new={new_df.run.job.account_id})"
        )

        LOGGER.warning(f"[tag:WAAFDFED60]{base_log} {msg}")
        sentry_sdk.capture_message(f"{msg} {base_log}")

    if new_df.run.job.connector_id != existing.run.job.connector_id:
        msg = (
            f"CRITICAL: Found existing matching DF {existing.id} whose "
            f"connector does not match new DF. Please investigate ASAP! "
            f"(old={existing.run.job.connector_id},"
            f"new={new_df.run.job.connector_id})"
        )

        LOGGER.warning(f"[tag:WAAFDFED70]{base_log} {msg}")
        sentry_sdk.capture_message(f"{msg} {base_log}")

    raise _DuplicateError(f"Duplicate Discovered File")
