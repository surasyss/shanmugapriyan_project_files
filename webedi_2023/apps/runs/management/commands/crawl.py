from django.core.management.base import BaseCommand

from apps.runs.management.commands import LOGGER
from apps.runs.models import Run
from apps.adapters import engine


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--run_id", action="store", dest="run_id", default=None, help="Run Id"
        )

    def handle(self, *args, **options):
        LOGGER.info(f'Received crawl command for run_id: {options.get("run_id")}')
        run = Run.objects.get(pk=options["run_id"])
        engine.crawl(run)
        LOGGER.info(f"Finished command for run_id: {run.id}")
