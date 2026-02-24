from django.conf import settings
from django.core.management.base import BaseCommand

from apps.definitions.models import ConnectorCapabilityTypes as CCT
from apps.jobconfig.models import Job
from apps.runs import maintenance
from apps.runs.management.commands import LOGGER
from apps.runs.models import RunCreatedVia


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--operations",
            action="store",
            dest="operations",
            default=None,
            help="Comma-separated Operations",
        )

        # optionally, it can also provide a comma-separated list of job_ids
        parser.add_argument(
            "--jobs",
            action="store",
            dest="jobs",
            default=None,
            help="Comma-separated Job Ids",
        )

        # this optional argument enables runs to be marked as created from admin (and avoid the additional
        # checks on scheduled runs if so needed)
        parser.add_argument(
            "--created_via",
            action="store",
            dest="created_via",
            default="scheduled",
            help="Created Via",
        )

    @staticmethod
    def _get_queryset_for_operation(operation: CCT, is_manual):
        if operation == CCT.INVOICE__DOWNLOAD:
            if is_manual:
                return Job.objects.runnable__invoice_download__manual()
            else:
                return Job.objects.runnable__invoice_download__automated()
        return Job.objects.runnable(operation)

    @staticmethod
    def _parse_job_ids(options: dict):
        job_ids = options.get("jobs")
        if job_ids:
            job_ids = [j.strip() for j in job_ids.split(",") if j.strip()]
        job_ids = job_ids or None
        return job_ids

    @staticmethod
    def _parse_operations(options: dict):
        operations = options.get("operations")
        if not operations:
            operations = ",".join(
                [
                    CCT.PAYMENT__EXPORT_INFO.ident,
                    CCT.INVOICE__DOWNLOAD.ident,
                    f"{CCT.INVOICE__DOWNLOAD.ident}:manual",
                ]
            )

        # parse string
        operations = [
            op.strip().split(":") for op in operations.split(",") if op.strip()
        ]
        operations = [
            (CCT.from_ident(op[0]), {"is_manual": True} if ("manual" in op) else {})
            for op in operations
        ]
        return operations

    def handle(self, *args, **options):
        LOGGER.info(
            f"Beginning to look for Jobs that must be run. "
            f"Provided options: {options}"
        )

        # parse options
        created_via = RunCreatedVia.from_ident(options["created_via"])
        job_ids = self._parse_job_ids(options)
        operations = self._parse_operations(options)

        for (op, kwargs) in operations:
            queryset = self._get_queryset_for_operation(op, kwargs.get("is_manual"))
            if job_ids:
                queryset = Job.objects.runnable(op).filter(pk__in=job_ids)

            try:
                created, skipped = maintenance.trigger_jobs(
                    op, created_via, queryset=queryset, **kwargs
                )
                LOGGER.info(
                    f"Submitted total {created} Jobs for async processing, skipped {skipped} for operation {op}"
                )
            except Exception as exc:
                msg = (
                    f"[tag:webedi-trigger-jobs-000] Hit an exception when trying to trigger jobs for "
                    f"operation=`{op}` created_via=`{created_via}`, "
                    f"kwargs=`{kwargs}`.\n"
                    f"Exception: `{exc}`"
                )
                settings.SLACK_CLIENT.message(settings.SLACK_CHANNEL, msg)
                LOGGER.info(msg)
