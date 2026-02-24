from selenium.webdriver.ie.webdriver import WebDriver

from apps.runs.models import Run


class ExecutionContext:
    def __init__(self, run: Run, **kwargs):
        self.run = run
        self.job = self.run.job
        self.connector = self.job.connector

        self.context = kwargs

        # frequently used, convenience members
        self.driver: WebDriver = kwargs.pop("driver", None)
        self.download_location = kwargs.pop("download_location", None)
