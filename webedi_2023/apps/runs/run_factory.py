from datetime import timedelta
from typing import Optional

import pytz
from django.utils import timezone

from apps.definitions.models import ConnectorType, EntityType, ConnectorCapabilityTypes
from apps.jobconfig.models import Job, JobSchedule
from apps.runs import LOGGER
from apps.runs.models import Run, RunStatus, RunCreatedVia
from django.conf import settings
from spices.django3.coreobjects.models import Company

__RUN_FACTORIES = {}


def run_factory(capability: ConnectorCapabilityTypes):
    def _decorator(factory_fn):
        __RUN_FACTORIES[capability] = factory_fn
        return factory_fn

    return _decorator


def create_run(
    job: Job, operation: ConnectorCapabilityTypes, created_via: RunCreatedVia, **params
) -> Optional[Run]:
    """
    Creates Run based on job and specified operation.
    This is the only allowed and supported entrypoint for creating Runs
    """
    if not job.connector.enabled:
        raise Exception(f"This connector is not enabled yet")

    if not job.connector.has_capability(operation):
        raise Exception(f"This connection doesn't support the operation: {operation}")

    if isinstance(operation, str):
        operation = ConnectorCapabilityTypes.from_ident(operation)

    factory = __RUN_FACTORIES.get(operation)
    if not factory:
        raise Exception(f"Unsupported operation: {operation}")

    run = factory(job, operation, created_via, **params)
    if run:
        LOGGER.info(f"Run {run.id} created for {job.id}")
    return run


# ########### RUN OBJECT CONSTRUCTION LOGIC #############


@run_factory(ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN)
def _create_run__login(
    job: Job, operation: ConnectorCapabilityTypes, created_via: RunCreatedVia, **kwargs
) -> Optional[Run]:
    return Run.objects.create(
        job=job,
        action=operation,
        created_via=created_via,
        request_parameters=kwargs,
        dry_run=True,
    )


@run_factory(ConnectorCapabilityTypes.INVOICE__DOWNLOAD)
def _create_run__invoice__download(
    job: Job, operation: ConnectorCapabilityTypes, created_via: RunCreatedVia, **kwargs
) -> Optional[Run]:
    suppress_invoices = kwargs.get("suppress_invoices", False)
    start_date = kwargs.get("start_date", str(settings.RUN_DEFAULT_START_DATE))
    end_date = kwargs.get("end_date", str(settings.RUN_DEFAULT_START_DATE.today()))
    is_manual = kwargs.get("is_manual", job.connector.is_manual)

    if is_manual:
        if not _should_create_run__invoice_download__manual(job, created_via):
            return None
    else:
        if not _should_create_run__invoice_download__automated(job, created_via):
            return None

    params = {
        "version": 1,
        "start_date": start_date,
        "end_date": end_date,
        "suppress_invoices": suppress_invoices,
    }

    return Run.objects.create(
        job=job,
        action=operation,
        created_via=created_via,
        request_parameters=params,
        is_manual=is_manual,
    )


@run_factory(ConnectorCapabilityTypes.PAYMENT__EXPORT_INFO)
def _create_run__payment__export(
    job: Job, operation: ConnectorCapabilityTypes, created_via: RunCreatedVia, **kwargs
) -> Optional[Run]:
    if not _should_create_run__payment_export(job, created_via):
        return None

    # TODO: This logic should become restaurant independent completely once
    #   this ticket is deployed. https://plateiq.atlassian.net/browse/PROD-3509
    parsed_json = {}
    companies = job.companies.all()

    if not companies:
        raise Exception(f"[tag:RUNS01] companies cannot be : None")

    for company in companies:
        company = Company.retrieve(None, company.remote_id, cache_locally=False)
        location_ids = list(map(lambda res: res["id"], company.restaurants))

        for location_id in location_ids:
            billpay_exported_response = settings.PIQ_CORE_CLIENT.billpay_export_dry_run(
                location_id
            )

            if billpay_exported_response is not None:
                parsed_json = __construct_parsed_json_for_exporting_payments(
                    parsed_json, billpay_exported_response
                )

    params = {"version": 2, "accounting": parsed_json}
    return Run.objects.create(
        job=job, action=operation, created_via=created_via, request_parameters=params
    )


@run_factory(ConnectorCapabilityTypes.ACCOUNTING__IMPORT_MULTIPLE_ENTITIES)
@run_factory(ConnectorCapabilityTypes.BANK_ACCOUNT__IMPORT_LIST)
@run_factory(ConnectorCapabilityTypes.GL__IMPORT_LIST)
@run_factory(ConnectorCapabilityTypes.VENDOR__IMPORT_LIST)
def _create_run__accounting__import_multiple(
    job: Job, operation: ConnectorCapabilityTypes, created_via: RunCreatedVia, **kwargs
) -> Optional[Run]:
    if not _should_create_run__accounting__import_multiple(job, created_via):
        return None

    if operation is ConnectorCapabilityTypes.ACCOUNTING__IMPORT_MULTIPLE_ENTITIES:
        operations = [
            ConnectorCapabilityTypes.BANK_ACCOUNT__IMPORT_LIST,
            ConnectorCapabilityTypes.GL__IMPORT_LIST,
            ConnectorCapabilityTypes.VENDOR__IMPORT_LIST,
        ]
    else:
        operations = [operation]

    entities = _get_import_entities(job, operations)

    if (
        job.connector.enabled
        and job.connector.type == ConnectorType.ACCOUNTING.ident
        and entities
    ):
        params = {"version": 1, "import_entities": entities}
        return Run.objects.create(
            job=job,
            action=operation,
            created_via=created_via,
            request_parameters=params,
        )

    return None


def _get_import_entities(job, operations):
    entities = []
    for op in operations:
        if not job.connector.has_capability(op):
            continue

        if op is ConnectorCapabilityTypes.BANK_ACCOUNT__IMPORT_LIST:
            entities.append(EntityType.BANK_ACCOUNT.ident)
        elif op is ConnectorCapabilityTypes.GL__IMPORT_LIST:
            entities.append(EntityType.GL_ACCOUNT.ident)
        elif op is ConnectorCapabilityTypes.VENDOR__IMPORT_LIST:
            entities.append(EntityType.VENDOR.ident)
        elif op is ConnectorCapabilityTypes.PAYMENT__IMPORT_INFO:
            entities.append(EntityType.PAYMENT.ident)
        else:
            raise Exception(f"Unexpected operation: {op}. This should never happen.")
    return entities


@run_factory(ConnectorCapabilityTypes.PAYMENT__IMPORT_INFO)
def _create_run__payment__import_info(
    job: Job, operation: ConnectorCapabilityTypes, created_via: RunCreatedVia, **kwargs
) -> Optional[Run]:
    _entity_types = (EntityType.PAYMENT.ident,)
    entities = _get_import_entities(job, [operation])

    if (
        job.connector.enabled
        and job.connector.type == ConnectorType.ACCOUNTING.ident
        and entities
    ):
        params = {"version": 1, "import_payments": True, "import_entities": entities}
        return Run.objects.create(
            job=job,
            action=operation,
            created_via=created_via,
            request_parameters=params,
        )

    return None


@run_factory(ConnectorCapabilityTypes.PAYMENT__PAY)
def _create_run__payment__make_payment(
    job: Job, operation: ConnectorCapabilityTypes, created_via: RunCreatedVia, **kwargs
):
    return Run.objects.create(
        job=job, action=operation, created_via=created_via, request_parameters=kwargs
    )


# ########### SCHEDULING LOGIC #############


def _should_create_run__invoice_download__automated(
    job: Job, created_via: RunCreatedVia
):
    """
    As we're running batch process per 3 hours, we want to minimize the o of crawl attempts at the
    websites, we've added following conditions for a job to create a run.
    """
    if created_via == RunCreatedVia.SCHEDULED:
        # just list down the cases in which case we should NOT be creating a run
        # for all other cases, default to yes

        latest_run = job.last_run
        tz = pytz.timezone(settings.TIME_ZONE)
        now = timezone.now().astimezone(tz=tz)
        queryset_12h = job.runs.filter(created_date__gte=now - timedelta(hours=12))

        # only returning True here to avoid too much nesting
        if not latest_run or latest_run.is_older_than(hours=24):
            return True

        # if a JobSchedule schedule exists, then defer the decision to it
        if job_schedule := JobSchedule.objects.filter(job=job).first():
            if job_schedule.match(now):
                now_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                queryset = job.runs.filter(
                    created_date__gte=now_start,
                    created_date__lt=now_start + timedelta(days=1),
                )

                # if we have had a success within the scheduled day,
                # don't schedule a new one
                if queryset.filter(status=RunStatus.SUCCEEDED.ident).exists():
                    return False

                # if multiple runs were already scheduled today,
                # don't schedule
                elif queryset.filter(is_manual=True).count() >= 3:
                    return False

                # otherwise we return true, because today is an important date
                else:
                    return True

        # if we have a success in last 24h, don't schedule
        if latest_run.status == RunStatus.SUCCEEDED.ident:
            return False

        # if already have scheduled runs that haven't started, don't schedule
        statuses = [
            RunStatus.CREATED.ident,
            RunStatus.SCHEDULED.ident,
        ]
        if queryset_12h.filter(status__in=statuses).exists():
            return False

        # if we have >=3 failed retries in last 12h, don't schedule
        status = RunStatus.FAILED.ident
        count = queryset_12h.filter(status=status).count()
        if count >= 3:
            return False

        # if we have >=3 partial successes in last 12h, don't schedule
        # the logic here is that if multiple runs are causing a partial
        #   success, something else is wrong
        status = RunStatus.PARTIALLY_SUCCEEDED.ident
        count = queryset_12h.filter(status=status).count()
        if count >= 3:
            return False

        # if latest run was in last 3h, we don't want to have a
        # higher retry frequency than that, so don't schedule
        if not latest_run.is_older_than(hours=3):
            return False

    # by default, return True
    return True


def _should_create_run__invoice_download__manual(job: Job, created_via: RunCreatedVia):
    if created_via == RunCreatedVia.SCHEDULED:
        tz = pytz.timezone(settings.TIME_ZONE)
        now = timezone.now().astimezone(tz=tz)

        if job_schedule := JobSchedule.objects.filter(job=job).first():
            if job_schedule.match(now):
                now_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
                now_end = now_start + timedelta(days=1)
                queryset = job.runs.filter(
                    created_date__gte=now_start, created_date__lt=now_end
                )

                # if we have had a success within the scheduled day,
                # don't schedule a new one
                if queryset.filter(status=RunStatus.SUCCEEDED.ident).exists():
                    return False

                # if multiple manual runs were already scheduled today,
                # don't schedule
                elif queryset.filter(is_manual=True).count() >= 3:
                    return False

                # otherwise we return true, because today is an important date
                else:
                    return True

        # at this point, we know that we don't have to worry about the
        # job_schedule, so we can proceed with normal scheduling

        # ##########

        # if latest run was in last 3h, we don't want to have a
        # higher retry frequency than that, so don't schedule
        queryset_3h = job.runs.filter(
            is_manual=True, created_date__gte=now - timedelta(hours=3)
        )
        if queryset_3h.exists():
            return False

        # if we have >=3 MANUAL retries in <frequency>, don't schedule
        frequency = job.connector.frequency or 1
        queryset_freq = job.runs.filter(
            created_date__gte=now - timedelta(days=frequency)
        )
        if queryset_freq.filter(is_manual=True).count() >= 3:
            return False

        # if we have ANY success in <frequency>, don't schedule
        if queryset_freq.filter(status=RunStatus.SUCCEEDED.ident).exists():
            return False

        # if we have existing not-started runs, don't schedule
        queryset_pending = job.runs.filter(
            created_date__gte=now - timedelta(hours=12),
            is_manual=True,
            status__in=[
                RunStatus.CREATED.ident,
                RunStatus.SCHEDULED.ident,
            ],
        )
        if queryset_pending.exists():
            return False

    return True


def _should_create_run__payment_export(job: Job, created_via: RunCreatedVia):
    if created_via == RunCreatedVia.SCHEDULED:
        now_minus_24h = timezone.now() - timedelta(hours=24)
        queryset = job.runs.filter(created_date__gte=now_minus_24h)

        # if there has been a successful run in the last 24h, return False
        if queryset.filter(status=RunStatus.SUCCEEDED.ident).exists():
            return False

        # if there have been >=3 failed runs in the last 24h, return False
        if queryset.filter(status=RunStatus.SUCCEEDED.ident).count() >= 3:
            return False

        # if there has been any run in the last 3h, return False,
        # we don't want to retry sooner than that
        now_minus_3h = timezone.now() - timedelta(hours=3)
        queryset = job.runs.filter(created_date__gte=now_minus_3h)
        if queryset.exists():
            return False

    return True


def _should_create_run__accounting__import_multiple(
    job: Job, created_via: RunCreatedVia
):
    if created_via == RunCreatedVia.SCHEDULED:
        now_minus_7d = timezone.now() - timedelta(days=7)
        queryset = job.runs.filter(created_date__gte=now_minus_7d)

        # if there has been a successful run in the last 7d, return False
        if queryset.filter(status=RunStatus.SUCCEEDED.ident).exists():
            return False

        # if there have been >=3 failed runs in the last 7d, return False
        if queryset.filter(status=RunStatus.SUCCEEDED.ident).count() >= 3:
            return False

        # if there has been any run in the last 1d, return False,
        # we don't want to retry sooner than that
        now_minus_1d = timezone.now() - timedelta(hours=24)
        queryset = job.runs.filter(created_date__gte=now_minus_1d)
        if queryset.exists():
            return False

    return True


# ########### PRIVATE #############


def __construct_parsed_json_for_exporting_payments(
    converted_dict: dict, input_json: dict
) -> dict:
    """
    Converts the BillPay Export API response into optimised json
    This method is only specific to Site Type = ACCOUTING
    @param: converted_dict: This is the optimised version of BillPay Export API response
    @param: input_json: This is the BillPay Export API response as it is
    returns: returns final optimised version of BillPay Export API response
    """

    LOGGER.info(f"Converting Billpay Export JSON response as per webedi...")

    for element in input_json["grouped_exports"]:
        if not element["data"]:
            LOGGER.info(
                f"Error while trying to create payment export run: "
                f"element['data'] is empty. Skipping element. "
                f"(element={element})"
            )
            continue
        payments = element["data"].items()
        for chequerun_id, value in payments:
            if chequerun_id in converted_dict:
                continue

            converted_dict[chequerun_id] = {}
            converted_dict[chequerun_id]["chequerun_id"] = value[0]["chequerun_id"]
            converted_dict[chequerun_id]["bank_account"] = value[0][
                "bank_account"
            ].strip()
            converted_dict[chequerun_id]["vendor_id"] = value[0]["vendor_id"].strip()
            converted_dict[chequerun_id]["vendor_name"] = value[0][
                "vendor_name"
            ].strip()
            converted_dict[chequerun_id]["location_id"] = value[0][
                "location_id"
            ].strip()
            converted_dict[chequerun_id]["payment_date"] = value[0][
                "payment_date"
            ].strip()
            converted_dict[chequerun_id]["payment_number"] = value[0][
                "payment_number"
            ].strip()
            converted_dict[chequerun_id]["payment_total"] = value[0]["payment_total"]
            converted_dict[chequerun_id]["invoices"] = []

            for item in value:
                if not item["invoice_number"]:  # skipping invoices with invoice# = Null
                    continue

                invoice = dict()
                invoice["invoice_number"] = item["invoice_number"].strip()
                invoice["invoice_date"] = item["invoice_date"].strip()
                invoice["invoice_amount"] = item["invoice_amount"]
                invoice["location_id"] = item["location_id"]

                converted_dict[chequerun_id]["invoices"].append(invoice)
    LOGGER.info(f"Input: {input_json}")
    LOGGER.info(f"Output: {converted_dict}")
    return converted_dict


def __construct_parsed_json_for_making_payments(
    converted_dict: dict, input_json: dict
) -> dict:
    """
    Converts the BillPay Payments API response into optimised json
    This method is only specific to Site Type = ACCOUTING
    @param: converted_dict: This is the optimised version of BillPay Payments API response
    @param: input_json: This is the BillPay Payments API response as it is
    returns: returns final optimised version of BillPay Payments API response
    """

    LOGGER.info(f"Converting Billpay Payments JSON response as per webedi...")
    LOGGER.info(f"Input: {input_json}")
    LOGGER.info(f"Output: {converted_dict}")
    return converted_dict
