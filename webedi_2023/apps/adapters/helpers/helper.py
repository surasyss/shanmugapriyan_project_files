"""Helper functions goes here"""

import os
import re
import shutil

import time
from typing import List
from zipfile import ZipFile

from integrator.settings import BASE_DIR
from apps.adapters.helpers import LOGGER


class ZeroFileSizeException(Exception):
    pass


def get_root_dir() -> str:
    """
    Returns the root absolute path of the current directory
    :return: The absolute path of the current working directory
    """
    absolute_path = os.path.abspath(os.path.join(BASE_DIR, ".."))
    LOGGER.info("Returning root directory path: %s", absolute_path)
    return absolute_path


def wait_until_file_exists_deprecated(actual_file: str, wait_time_in_seconds=10):
    """
    Waits until files exists at location
    :param actual_file: Full path & name of the file
    :param wait_time_in_seconds: No. of seconds to wait for checking the file again
    :return: Nothing
    """
    waits = 0
    while not os.path.isfile(actual_file) and waits < wait_time_in_seconds:
        LOGGER.info("Waiting till the file gets downloaded... %s", str(waits))
        sleep(1, msg="for file download")  # make sure file completes downloading
        waits += 1


def wait_until_file_exists(
    file_path: str,
    timeout: float,
    pattern: str = None,
    delay: float = 0.5,
    backoff: float = 2,
) -> str:
    """
    Returns filename as soon as a file exists at the given path. Waits for a maximum of `timeout` seconds, or raises
    TimeoutError
    :param file_path: Full path of the file
    :param timeout: Maximum time in seconds to wait for the file to appear
    :param pattern: Find files based on patterns
    :param delay: Delay in seconds between subsequent checks
    :param backoff: Multiplicative factor to apply to increase delay between subsequent checks
    """
    assert backoff >= 1, "Backoff factor can not be less than 1"
    assert timeout >= 0, "Need a positive timeout"

    start_time = time.time()

    while time.time() - start_time < timeout:
        if pattern:
            file = next(
                (file for file in os.listdir(file_path) if re.search(pattern, file)),
                None,
            )
            if file:
                return os.path.join(file_path, file)

        if os.path.isfile(file_path):
            return file_path

        LOGGER.debug(f"Waiting for {delay} seconds for file {file_path}")
        time.sleep(delay)
        delay *= backoff

    raise TimeoutError(f"Timed out while waiting for file to exist: {file_path}")


def sleep(time_in_secs: float, msg: str = ""):
    """
    Wait for X seconds
    :param time_in_secs: Time in Seconds
    :param msg: Additional info eg. why using sleep
    """
    LOGGER.info(f"Sleeping for {time_in_secs} seconds - {msg}")
    time.sleep(time_in_secs)


def rename_file(file_name: str, new_file_name: str):
    """
    Rename/Move the file
    :param file_name: Input file name
    :param new_file_name: New File name to be updated
    :return: Nothing
    """
    LOGGER.info("Renaming the file: %s to %s", file_name, new_file_name)
    shutil.move(file_name, new_file_name)


def validate_downloaded_files(expected_files_list: list) -> list:
    """
    Validates the files are present at the downloaded location
    :param expected_files_list: List of files to be validated
    :return: Nothing
    """
    failed_file_downloading = [f for f in expected_files_list if not os.path.isfile(f)]
    if expected_files_list:
        if failed_file_downloading:
            LOGGER.error(
                "Checked: These files are not present at the location => %s",
                str(failed_file_downloading),
            )
        else:
            LOGGER.info("Checked: All files are downloaded successfully.")
    else:
        LOGGER.warning(
            "Something is wrong or there is no document for download. Downloaded File count is ZERO."
        )
    return failed_file_downloading


def extract_zip_file(file_path: str) -> List[str]:
    """
    Extracts the zip file contents
    :param file_path: Full path of the file/dir path in case searching files with the pattern
    :param pattern: Optional, searches file with this pattern
    """
    LOGGER.info(f"Extracting file: {file_path}")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File Path doesn't exist: {file_path}")

    dir_path = os.path.split(file_path)[0]
    with ZipFile(file_path, "r") as zip_obj:
        file_list = zip_obj.namelist()
        zip_obj.extractall(dir_path)
        LOGGER.info(f"Extracted file: {file_path}")
        return file_list

    return None


def delete_files(file_path: str, pattern: str = None):
    """
    Deletes the files
    :param file_path: Full path of the file/dir path in case searching files with the pattern
    :param pattern: Optional, searches file with this pattern
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Folder not found: {file_path}")

    if not pattern:
        os.remove(file_path)
        LOGGER.info(f"Deleted file: {file_path}")
        return

    for file in os.listdir(file_path):
        if re.search(pattern, file):
            os.remove(os.path.join(file_path, file))
            LOGGER.info(f"Deleted file: {os.path.join(file_path, file)}")
            return

    LOGGER.warning(f"File deletion failed. File with pattern: {pattern} not found!")
