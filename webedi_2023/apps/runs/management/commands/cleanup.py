from django.conf import settings
from django.core.management.base import BaseCommand

from apps.runs import maintenance, tasks
from apps.runs.management.commands import LOGGER


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--operations",
            action="store",
            dest="operations",
            default=None,
            help="Comma-separated list of operations",
        )

    def handle(self, *args, **options):
        operations = options.get("operations") or ""
        operations = {op.strip() for op in operations.split() if op.strip()}
        if not operations:
            operations = {
                "reschedule_existing_runs",
                "prune_runs",
                "prune_manual_runs",
                "create_invoices",
                "delete_run_files",
                "convert_connector_requests",
                "disable_failing_checkruns",
            }

        if "reschedule_existing_runs" in operations:
            succeeded, failed = maintenance.reschedule_existing_runs()
            if succeeded or failed:
                LOGGER.warning(
                    f"[tag:webedi-cleanup-000] Found runs in CREATED state, scheduled {succeeded} (failed: {failed})"
                )

        if "prune_runs" in operations:
            succeeded, failed = maintenance.prune_runs__cancel_if_multiple_scheduled()
            if succeeded or failed:
                LOGGER.warning(
                    f"[tag:webedi-cleanup-010] Cancelled {succeeded} duplicate scheduled runs (failed: {failed})"
                )

            succeeded, failed = maintenance.prune_runs__retrigger_if_stuck_in_started()
            if succeeded or failed:
                LOGGER.warning(
                    f"[tag:webedi-cleanup-020] Retriggered {succeeded} stuck runs (failed: {failed})"
                )

        if "prune_manual_runs" in operations:
            (
                succeeded,
                failed,
            ) = maintenance.prune_manual_runs__cancel_if_scheduled_long_ago()
            if succeeded or failed:
                LOGGER.warning(
                    f"[tag:webedi-cleanup-030] Cancelled {succeeded} manual runs which were very old "
                    f"but not processed (failed: {failed})",
                )

        if "create_invoices" in operations:
            succeeded, failed = maintenance.create_invoices()
            if failed:
                LOGGER.warning(
                    f"[tag:webedi-cleanup-040] Created {succeeded} invoices from DFs pending processing (failed: {failed})"
                )

        if "delete_run_files" in operations:
            # We have to run this in a celery task because the cleanup needs to happen
            #   wherever celery workers are running, not where current process is running.
            # Of course, there's still the possibility that there could be multiple EC2 instances, and the one
            #   that's getting cleaned up is only the one which picks up this task. But we ignore that for now.
            tasks.delete_run_files_task.delay()

        if "convert_connector_requests" in operations:
            succeeded, failed = maintenance.convert_connector_requests()
            if succeeded or failed:
                LOGGER.warning(
                    f"[tag:webedi-cleanup-050] Converted {succeeded} connector requests to connectors/jobs (failed: {failed})"
                )

        if "disable_failing_checkruns" in operations:
            (
                disabled_count,
                suspect_count,
                failed,
            ) = maintenance.disable_failing_checkruns()
            if disabled_count or failed:
                msg = (
                    f"[tag:webedi-cleanup-060] Disabled {disabled_count} checkruns which were failing "
                    f"continuously. Found {suspect_count} more suspects."
                )
                if failed:
                    msg += f" Had {failed} failures while trying to disable checkruns."

                LOGGER.warning(msg)
