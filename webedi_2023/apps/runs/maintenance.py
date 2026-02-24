import logging
import os
from datetime import timedelta, datetime

import time
from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from apps.adapters import file_actions
from apps.adapters.file_actions import SkipProcessing
from apps.definitions.models import ConnectorCapabilityTypes, Connector
from apps.jobconfig.models import Job, ConnectorRequest
from apps.runs.models import (
    RunStatus,
    Run,
    RunCreatedVia,
    RunCancellationReason,
    DiscoveredFile,
    CheckRun,
)
from apps.runs.run_factory import create_run
from spices.django3.accounts.models import User

LOGGER = logging.getLogger("apps.runs.tasks")


def reschedule_existing_runs():
    LOGGER.info(f"[tag:WARTPRRER10] Looking for CREATED runs to schedule")
    created = RunStatus.CREATED.ident  # pylint: disable=no-member

    # don't look for runs older than 3 days. Let bygones be bygones.
    runs = Run.objects.filter(
        status=created,
        created_date__gt=timezone.now() - timedelta(days=3),
        created_date__lte=timezone.now() - timedelta(hours=1),
    )
    succeeded = 0
    failed = 0

    for run in runs:
        on_demand = run.created_via in (
            RunCreatedVia.ADMIN_REQUEST,
            RunCreatedVia.CUSTOMER_REQUEST,
        )
        try:
            run.execute_async(on_demand=on_demand)
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.info(f"[tag:WARTPRRER20] Exception trying to schedule run {run}")

    LOGGER.info(
        f"[tag:WARTPRRER30] Scheduled {succeeded} runs because"
        f" they were in CREATED state (failed: {failed})"
    )

    return succeeded, failed


def prune_runs__cancel_if_multiple_scheduled():
    """If a job has multiple scheduled runs, cancel all but the latest scheduled runs (except admin-created runs)"""

    LOGGER.info(f"[tag:WARTPRCMS10] Looking for duplicate scheduled runs to cancel")
    scheduled = RunStatus.SCHEDULED.ident  # pylint: disable=no-member

    jobs = (
        Run.objects.values("job_id")
        .annotate(cnt=Count("id"))
        .filter(status=scheduled, cnt__gt=1)
        .exclude(created_via=RunCreatedVia.ADMIN_REQUEST)
    )

    succeeded = 0
    failed = 0
    for job in jobs:
        runs = (
            Run.objects.filter(status=scheduled, job__id=job["job_id"])
            .filter(created_date__gt=timezone.now() - timedelta(days=3))
            .exclude(created_via=RunCreatedVia.ADMIN_REQUEST)
            .order_by("-created_date")
        )
        for run in runs[1:]:
            try:
                run.cancel(
                    RunCancellationReason.SCHEDULED_MULTIPLE,
                    "Cancelled by system since multiple runs are scheduled for the same job",
                    canceled_by=None,
                )
                succeeded += 1
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.exception(
                    f"[tag:WARTPRCMS20] Exception trying to cancel and duplicate run: {exc}"
                )
                failed += 1

    LOGGER.info(
        f"[tag:WARTPRCMS30] Cancelled {succeeded} runs because they were duplicates (failed: {failed})"
    )
    return succeeded, failed


def prune_runs__retrigger_if_stuck_in_started():
    """If a job has runs that were started but haven't finished yet, cancel and re-trigger the STARTED jobs"""
    LOGGER.info(f"[tag:WARTPRCSS10] Looking for (stuck) runs to cancel and re-create")

    runs = Run.objects.filter(
        status=RunStatus.STARTED.ident,  # pylint: disable=no-member
        created_date__gt=timezone.now() - timedelta(days=3),
        execution_start_ts__lt=timezone.now() - timedelta(hours=4),
    )

    succeeded = 0
    failed = 0
    retriggered_job_ids = set()

    for run in runs:
        try:
            run.cancel(
                RunCancellationReason.STARTED_TIMED_OUT,
                "Cancelled by system(cron), because run was in started state since long time.",
                canceled_by=User.objects.get(username="webedi-worker"),
            )

            if run.job_id in retriggered_job_ids:
                # if we cancel 5 instances of a job's run, we don't want to re-trigger 5 times
                LOGGER.info(
                    f"[tag:WARTPRCSS12] Skip re-triggering {run.id} since another run has already been created"
                )
            else:
                new_run = run.duplicate()
                retriggered_job_ids.add(
                    run.job_id
                )  # add to set of re-triggered jobs AFTER creating record

                LOGGER.info(
                    f"[tag:WARTPRCSS15] Triggering run {new_run.id} as replacement for {run.id}"
                )
                new_run.execute_async()

            succeeded += 1
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.exception(
                f"[tag:WARTPRCSS20] Exception trying to cancel and duplicate run: {exc}"
            )
            failed += 1

    LOGGER.info(
        f"[tag:WARTPRCSS30] Cancelled and retriggered {succeeded} runs "
        f"that were stuck in STARTED state (failed {failed})"
    )
    return succeeded, failed


def create_invoices():
    LOGGER.info(
        "[tag:WARTCI10] Beginning to look for Discovered files for which PIQ invoices must be created"
    )
    discovered_files = DiscoveredFile.objects.filter(
        downloaded_successfully=True,
        piq_container_id__isnull=True,
        created_date__lt=timezone.now() - timedelta(hours=4),
    ).exclude(run__request_parameters__suppress_invoices=True)

    succeeded = 0
    failed = 0
    for discovered_file in discovered_files:
        run = discovered_file.run
        LOGGER.info(
            f"[tag:WARTCI20][run:{run.id}][df:{discovered_file.id}] Post-processing DF"
        )
        try:
            file_actions.factory(discovered_file).execute()
            LOGGER.info(
                f"[tag:WARTCI30][run:{run.id}][df:{discovered_file.id}] Successfully post-processed DF"
            )
            succeeded += 1
        except SkipProcessing as exc:
            LOGGER.warning(
                f"[tag:WARTCI35][run:{run.id}][df:{discovered_file.id}] "
                f"Skipping processing discovered file"
            )
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.exception(f"Exception while post-processing DF: {exc}")
            failed += 1

    LOGGER.info(
        f"[tag:WARTCI30] Successfully post-processed {succeeded} discovered files (failed: {failed})"
    )
    return succeeded, failed


def delete_run_files():
    LOGGER.info(
        f"[tag:WARTDRF10] Beginning to remove files from {settings.TEMP_DOWNLOAD_DIR} which older than "
        f"{settings.REMOVE_FILES_OLDER_THAN_MINUTES} minutes"
    )

    removed_count = 0
    now = time.time()
    cutoff = now - (settings.REMOVE_FILES_OLDER_THAN_MINUTES * 60)
    for path, sub_dirs, files in os.walk(settings.TEMP_DOWNLOAD_DIR):
        for name in files:
            file_path = os.path.join(path, name)
            # delete file if older than cut off time.
            if os.stat(file_path).st_ctime < cutoff:
                os.remove(str(file_path))
                LOGGER.info(f"[tag:WARTDRF20] Removed file from filepath: {file_path}")

        # removing empty folders.
        for subdir in sub_dirs:
            file_path = os.path.join(path, subdir)
            if not os.listdir(file_path):
                os.rmdir(file_path)
                LOGGER.info(
                    f"[tag:WARTDRF30] Removed directory from filepath: {file_path}"
                )

    LOGGER.info(f"[tag:WARTDRF40] Deleted {removed_count} files.")
    return removed_count


def convert_connector_requests():
    LOGGER.info(f"Beginning to convert connector requests to jobs")
    succeeded = 0
    failed = 0
    connector_requests = ConnectorRequest.objects.all()
    for connector_request in connector_requests:
        try:
            if not connector_request.converted_to_connector:
                connectors = Connector.objects.filter(
                    login_url__icontains=connector_request.login_url,
                    name__icontains=connector_request.name,
                )
                if len(connectors) == 1:
                    connector = connectors[0]
                elif len(connectors) > 1:
                    LOGGER.warning(
                        f"[tag:CCRJ][SKIPPED][CRID:{connector_request.id}] Multiple connectors are present"
                    )
                    failed += 1
                    continue
                else:
                    LOGGER.warning(
                        f"[tag:CCRJ][SKIPPED][CRID:{connector_request.id}] No connector found"
                    )
                    failed += 1
                    continue

                connector_request.converted_to_connector = connector
                connector_request.save()

            LOGGER.info(
                f"[tag:CCRJ][FOUND_CONNECTOR][CRID:{connector_request.id}]Converting to Job"
            )
            connector_request.convert_to_job()
            succeeded += 1
        # pylint: disable=broad-except
        except Exception as exc:
            failed += 1
            LOGGER.warning(
                f"[tag:CCRJ][FAILED][CRID:{connector_request.id}] Failed converting to job"
                f" with exception : {exc}"
            )
    LOGGER.info(f"Finished convert connector requests to jobs")
    return succeeded, failed


def disable_failing_checkruns():
    now = timezone.now()
    LOGGER.info(
        f"[tag:WARTDFC10] Looking for CheckRuns that have been failing "
        f"consistently that can be safely disabled (now: {now})"
    )
    now_minus_1h = now - timedelta(hours=1)
    now_minus_1d = now - timedelta(days=1)
    now_minus_60d = now - timedelta(days=60)

    disabled_count = 0
    suspect_count = 0
    failed = 0

    prospects = (
        CheckRun.objects.filter(created_date__gte=now_minus_1d)
        .filter(created_date__lt=now_minus_1h)  # might not have finished yet
        .filter(is_disabled__isnull=True)  # only the NULL ones
        .exclude(is_checkrun_success=True)
        .select_related("run")
    )
    old_qs_base = CheckRun.objects.filter(created_date__gte=now_minus_60d)

    LOGGER.info(f"[tag:WARTDFC20] Evaluating {prospects.count()} prospects to disable")
    for checkrun in prospects.iterator(chunk_size=50):
        piq_chequerun_id = checkrun.check_run_id
        try:
            # note that we don't care about Job/Account level because
            # chequerun_id is from Core andd guaranteed to be unique
            old_queryset = old_qs_base.filter(check_run_id=piq_chequerun_id)

            if old_queryset.filter(is_disabled=True).exists():
                # skip because it's disabled anyway
                LOGGER.info(
                    f"[tag:WARTDFC30][cr:{checkrun.id}] CheckRun was "
                    f"disabled before, shouldn't have run anyway, skipping"
                )
                checkrun.mark_not_disabled()
                continue

            if old_queryset.filter(is_checkrun_success=True).exists():
                # skip because it's already successful
                LOGGER.info(
                    f"[tag:WARTDFC30][cr:{checkrun.id}] CheckRun has "
                    f"succeeded before, skipping"
                )
                checkrun.mark_not_disabled()
                continue

            first = old_queryset.order_by("created_date").first()
            if first.created_date > now - timedelta(days=45):
                # hasn't been retried for long enough
                if first.created_date < now - timedelta(days=30):
                    LOGGER.info(
                        f"[tag:WARTDFC30][cr:{checkrun.id}] CheckRun is "
                        f"suspect (first run was on {first.created_date})"
                    )
                    suspect_count += 1
                else:
                    # only mark not-disabled if it's not suspect
                    checkrun.mark_not_disabled()
                continue

            attempt_count = old_queryset.count()
            if attempt_count < 45:
                # hasn't been retried enough number of times
                if attempt_count > 30:
                    LOGGER.info(
                        f"[tag:WARTDFC40][cr:{checkrun.id}] CheckRun is "
                        f"suspect (total retries so far: {attempt_count})"
                    )
                    suspect_count += 1
                else:
                    # only mark not-disabled if it's not suspect
                    checkrun.mark_not_disabled()
                continue

            run = checkrun.run
            cr_dict = run.request_parameters["accounting"]
            payment_date = datetime.strptime(
                cr_dict[str(piq_chequerun_id)]["payment_date"], "%m/%d/%Y"
            )
            payment_date = payment_date.replace(tzinfo=now.tzinfo)
            if payment_date > now - timedelta(days=100):
                # payment is from the last 3 months, might be still relevant
                if payment_date < now - timedelta(days=60):
                    LOGGER.info(
                        f"[tag:WARTDFC40][cr:{checkrun.id}] CheckRun is "
                        f"suspect (Payment date over 60d old {payment_date})"
                    )
                    suspect_count += 1
                else:
                    # only mark not-disabled if it's not suspect
                    checkrun.mark_not_disabled()
                continue

            # if after all that we still have the checkrun, disable it
            LOGGER.info(f"[tag:WARTDFC50][cr:{checkrun.id}] Disabling checkrun")
            checkrun.mark_disabled()
            disabled_count += 1
        except Exception as exc:
            failed += 1
            LOGGER.warning(
                f"[tag:WARTDFC60][cr:{checkrun.id}] Failed to disable "
                f"checkrun with {type(exc).__name__}: {exc}"
            )

    LOGGER.info(
        f"[tag:WARTDFC70] Finished disable_failing_checkruns "
        f"(disabled:{disabled_count}, suspects:{suspect_count}, "
        f"failed:{failed})"
    )
    return disabled_count, suspect_count, failed


def trigger_jobs(
    operation: ConnectorCapabilityTypes,
    created_via: RunCreatedVia,
    queryset=None,
    **kwargs,
):
    """
    Single entry point for scheduling jobs.
    # TODO: If created_via == SCHEDULED, then this function should automatically take care of duplicates, etc etc

    :param operation: The operation to perform
    :param created_via: This is always SCHEDULED unless the developer is running it manually from ssh console
    :param queryset: Optional, used if there is a different queryset to be triggered than default

    :return: Count of successful and skipped jobs
    """
    LOGGER.info(
        f"[tag:WEARMTJ10] Looking for runnable Jobs for "
        f"operation='{operation}', created_via={created_via}, kwargs={kwargs}"
    )
    kwargs.setdefault("dry_run", False)

    # build queryset
    if queryset is None:
        queryset = Job.objects.runnable(operation)

    LOGGER.info(f"[tag:WEARMTJ15] Using queryset {queryset.query}")

    # trigger
    created = 0
    skipped = 0
    for job in queryset:
        LOGGER.info(f"[tag:WEARMTJ20] Run requested for Job id {job.id}")
        run = create_run(job, operation, created_via, **kwargs)
        if run:
            created += 1
            if not run.is_manual:
                run.execute_async()
        else:
            skipped += 1

    LOGGER.info(
        f"[tag:WEARMTJ30] Submitted total {created} Jobs for async processing, skipped {skipped}"
    )

    return created, skipped


def prune_manual_runs__cancel_if_scheduled_long_ago():
    """If runs are created more than 3 days ago,
    cancel all but the latest scheduled runs (except admin-created runs)"""

    LOGGER.info(f"[tag:WARTPRMRCICOT10] Looking for duplicate scheduled runs to cancel")
    scheduled = RunStatus.SCHEDULED.ident  # pylint: disable=no-member
    succeeded = 0
    failed = 0
    runs = (
        Run.objects.filter(status=scheduled)
        .filter(is_manual=True, created_date__lt=timezone.now() - timedelta(days=3))
        .exclude(created_via=RunCreatedVia.ADMIN_REQUEST)
        .order_by("-created_date")
    )
    for run in runs:
        try:
            run.cancel(
                RunCancellationReason.SCHEDULED_TIMED_OUT,
                "Cancelled by system, since manual run was scheduled more than 3 days ago",
                canceled_by=None,
            )
            succeeded += 1
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.exception(
                f"[tag:WARTPRMRCICOT20] Exception trying to cancel manual run: {exc}"
            )
            failed += 1

    LOGGER.info(
        f"[tag:WARTPRMRCICOT30] Cancelled {succeeded} manual runs because they were older than 3 days"
        f" and not processed (failed: {failed})"
    )
    return succeeded, failed
