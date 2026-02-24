from environ import environ

from apps.definitions.models import ConnectorCapabilityTypes, Connector
from tests.apps.definitions.factories import ConnectorFactory
from tests.apps.jobconfig.factories import JobFactory
from tests.apps.runs.factories import RunFactory

mock_connectors = [
    "always-fail-with-credential-error",
    "always-fail-with-partner-error",
    "slow-crawl",
    "success-N-files-found",
]


def get_crawler_credentials():
    env = environ.Env()
    env.read_env(f"{str(environ.Path(__file__) - 3)}/crawler_env.env")
    crawl_items = list()
    for item, value in env.ENVIRON.items():
        if "job" in item:
            v = env.dict(item)
            crawl_items.append(
                {
                    "adapter_code": v.get("adapter_code"),
                    "url": v.get("url"),
                    "username": v.get("username"),
                    "password": v.get("password"),
                }
            )
    return crawl_items


def crawler_factory():
    run_list = []
    credentials = get_crawler_credentials()
    for cred in credentials:
        if cred["adapter_code"] == "mock":
            for mock_connector in mock_connectors:
                run = get_run_from_adapter(cred["url"], cred, mock_connector)
                run_list.append(run)
        else:
            run = get_run_from_adapter(cred["url"], cred)
            run_list.append(run)

    return run_list


def get_run_from_adapter(url, value, mock_connector=None):
    connector = Connector.objects.filter(adapter_code=value["adapter_code"])
    if not connector:
        connector = ConnectorFactory(adapter_code=value["adapter_code"], login_url=url)
        if mock_connector:
            connector = ConnectorFactory(
                adapter_code=value["adapter_code"], login_url=url, name=mock_connector
            )
        connector = [connector]
    job = JobFactory(
        connector=connector[0], username=value["username"], password=value["password"]
    )
    run = RunFactory(job=job, action=ConnectorCapabilityTypes.INVOICE__DOWNLOAD)
    return run
