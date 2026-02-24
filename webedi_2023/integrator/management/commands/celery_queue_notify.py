from distutils.util import strtobool

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from spices.celery_utils import get_queue_length

from integrator.celery import celery_app
from integrator.management.commands import LOGGER


class Command(BaseCommand):
    QUEUES = [
        "integrator-tasks",
        "integrator-short-tasks",
        "integrator-tasks-on-demand",
    ]

    def add_arguments(self, parser):
        parser.add_argument("--queues", dest="queues", help="Celery Queue Names")

        parser.add_argument(
            "--notify-threshold",
            dest="notify_threshold",
            default=None,
            help="Queue length threshold for sending notification on slack.",
        )

        parser.add_argument(
            "--notify",
            dest="notify",
            default="False",
            help="Send notification on Slack",
        )

    def handle(self, *args, **options):
        notify = strtobool(options.get("notify", "False"))
        notify_threshold = options.get("notify_threshold", None)
        queues = options.get("queues", None)

        if notify and not notify_threshold:
            raise Exception("To enable notify please pass 'notify-threshold' as well")

        try:
            if notify_threshold:
                notify_threshold = int(notify_threshold)
        except ValueError:
            raise ValueError("notify-threshold must be a number")

        if not queues:
            queues = self.QUEUES

        LOGGER.info(f"{timezone.now()}: Fetching queue lengths")
        queue_length = get_queue_length(queues, celery_app)

        for queue, length in queue_length.items():
            LOGGER.info(f"Queue: {queue}; Number of tasks: {length}")

            if notify and length > notify_threshold:
                LOGGER.info(
                    f"[tag:webedi-notify-000] :exclamation: Alert - Pending tasks in queue {queue} is {length}"
                )

        LOGGER.info(f"Done")
