import shutil
from os import path

import pytest
from environ import environ

from apps.adapters import engine
from apps.runs.models import DiscoveredFile
from tests.crawl.factories import crawler_factory


@pytest.mark.skipif(
    not path.exists(f"{str(environ.Path(__file__) - 3)}/crawler_env.env"),
    reason="Shouldn't test in unit test pipeline.",
)
def test__crawlers_for_discovered_files():
    run_list = crawler_factory()
    df_path = f"{str(environ.Path(__file__) - 1)}/discovered_files"
    for run in run_list:
        print(f"run data : {run.__dict__}")
        try:
            engine.crawl(run)
            discovered_files = DiscoveredFile.objects.filter(run=run)
            for discovered_file in discovered_files:
                print(f"df data : {discovered_file.__dict__}")

            if path.exists(df_path):
                shutil.rmtree(df_path)
        except Exception as e:
            print(
                f"Failed for connector : {run.job.connector.name} with exception : {e}"
            )
            continue
