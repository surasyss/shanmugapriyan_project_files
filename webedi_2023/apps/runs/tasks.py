import logging

from django.conf import settings

from apps.adapters import engine
from apps.runs import maintenance
from apps.runs.models import Run, InvalidStatusForOperation
from integrator.celery import celery_app
from spices.http_utils import get_new_retryable_session_500

LOGGER = logging.getLogger("apps.runs.tasks")


@celery_app.task(queue="integrator-tasks", soft_time_limit=60 * 60, time_limit=90 * 60)
def execute_run(run_id: str):
    _run_crawl(run_id)


def _run_crawl(run_id, on_demand=False):
    LOGGER.info(
        f"[tag:INTRUNTER10][run:{run_id}] Received execute request (on_demand:{on_demand})"
    )

    run = Run.objects.get(pk=run_id)
    LOGGER.info(f"[tag:INTRUNTER10][run:{run_id}] Current run status is {run.status}")

    try:
        engine.crawl(run)
        LOGGER.info(f"[tag:INTRUNTER30][run:{run_id}] Finished execution.")
    except InvalidStatusForOperation as exc:
        LOGGER.warning(
            f"[tag:INTRUNTER20][run:{run_id}] Run is in invalid state, ignoring. (exc: {exc})"
        )


@celery_app.task(queue="integrator-short-tasks", max_retries=10, time_limit=900)
def send_to_step_function(payload):
    run_id = payload.get("run_id")
    job_id = payload.get("job").get("id")

    session = get_new_retryable_session_500(raise_on_status=False)
    edi_url = f"{settings.EDI_STEP_FUNCTION_URL}process_payment"
    response = session.post(edi_url, json=payload)

    if response.status_code >= 300:
        message = (
            f"[tag:INTRUNTER30] Run:{run_id}. Job: {job_id} StepFunction Creation failed with error "
            f"{response.status_code}: {response.content} for payload: {payload}"
        )
        LOGGER.error(message)

        raise Exception(message)

    LOGGER.info(
        f"[tag:INTRUNTER40] Run:{run_id}. Job: {job_id} Sent the payload {payload} to step function"
    )


@celery_app.task(
    queue="integrator-tasks-on-demand", soft_time_limit=60 * 60, time_limit=60 * 60
)
def execute_run_on_demand(run_id: str):
    _run_crawl(run_id, on_demand=True)


@celery_app.task(queue="integrator-short-tasks", time_limit=900)
def send_email(email_data: dict):
    LOGGER.info(f"Emails are disabled!!! hence not sending any email {email_data}")
    # EmailCoreClient(email_data['to_email'], email_data['subject']).send_generic_email(
    #     email_data['content'])


@celery_app.task(queue="integrator-short-tasks")
def delete_run_files_task():
    deleted = maintenance.delete_run_files()
    if deleted:
        LOGGER.info(
            f"[tag:webedi-tasks-000] Deleted {deleted} stale files for older runs"
        )
