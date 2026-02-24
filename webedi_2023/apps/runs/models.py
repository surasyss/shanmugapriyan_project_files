# pylint: disable=no-member

import hashlib
import json
import os
import time
from datetime import timedelta
from typing import Optional

import textract
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from spices.django3 import storage_utils
from spices.django3.base_model.models import BaseModel, model_prefix, SoftDeleteModel
from spices.django3.conf import LOCAL_ENV
from spices.django3.fields import TextChoiceField, CharChoiceField
from spices.django3.issues.models import Issue
from spices.django3.validators import validate_not_blank_string__allow_null
from spices.documents import DocumentType
from spices.enum_utils import BaseChoice
from spices.services import ContextualError

from apps.definitions.models import (
    Connector,
    EntityType,
    ConnectorType,
    ConnectorCapabilityTypes,
    SupportedCustomProperties,
)
from apps.error_codes import ErrorCode
from apps.jobconfig.models import Job, FileDiscoveryAction
from apps.runs import LOGGER

EMAIL_TEMPLATES = {
    "initial-success": {
        "subject": "Your connection with {connector_name} was successful!",
        "content": "Hi {first_name},<br><br>"
        "We successfully established a connection with {connector_name} for the username: {username}. "
        "Invoices found in the vendor portal will appear in your dashboard soon.<br><br>"
        "If we are unable to identify the location for an invoice, "
        'they\'ll go to the "Unmapped Locations" section of the To-Do List. '
        "Otherwise, invoices will be pulled daily and will appear in the Invoices tab.<br><br>",
    },
    "initial-failure": {
        "subject": "Your connection with {connector_name} failed. Please try again.",
        "content": (
            "Hi {first_name},<br><br>"
            "We were unable to establish a connection with {connector_name} for the username: {username}. "
            "Please try again.<br><br><br>"
            '<a target="_blank" style="background:#0874bf;text-decoration:none;'
            'padding: 16px;color:#ffffff;border-radius: 5px;" '
            'href="https://app.plateiq.com/#/site/settings/vendor-connections">'
            "Connect with {connector_name}</a><br><br>"
        ),
    },
    "operational-success": {
        "subject": "Vendor Connection with {connector_name} succeeded!",
        "content": (
            "Hi {first_name},<br><br>"
            "Your connection with {connector_name} (username: {username}), which had failed earlier, "
            "is again back up and successfully working!<br><br>"
            "This notification is for your information only, there is no action required on your part.<br>"
        ),
    },
    "operational-failure": {
        "subject": "Invoice sync failed for {connector_name}",
        "content": (
            "Hi {first_name},<br><br>"
            "We were unable to download invoices from {connector_name} using username: {username}. "
            "We'll try connecting again tomorrow.<br><br>"
            "Our engineering team has already been notified and is looking into this issue. "
            "There is no action required on your part.<br><br>"
        ),
    },
    "credential-issue": {
        "subject": "Action Required: Invoice sync failed for {connector_name} due to invalid credentials",
        "content": (
            "Hi {first_name},<br><br>"
            "We were unable to login to {connector_name} with username {username} "
            "due to invalid credentials.<br><br>"
            "Invoices from {connector_name} cannot be synced without working credentials.<br><br>"
            "<strong>Please reply to this email so we can update your connection "
            "with new credentials on your behalf.</strong)<br><br>"
        ),
    },
    "connector-request-enabled-success": {
        "subject": "Request to connect with {connector_name} was successful!",
        "content": "Hi {first_name},<br><br>"
        "We successfully established a connection with {connector_name} for the username: {username}. "
        "Invoices found in the vendor portal will appear in your dashboard soon.<br><br>"
        "If we are unable to identify the location for an invoice, "
        'they\'ll go to the "Unmapped Locations" section of the To-Do List. '
        "Otherwise, invoices will be pulled daily and will appear in the Invoices tab.<br><br>",
    },
    "connector-request-enabled-failure": {
        "subject": "Action Required: Request to connect with {connector_name} failed",
        "content": (
            "Hi {first_name},<br><br>"
            "We were unable to establish a connection with {connector_name} using username, {username}.<br><br>"
            "Please try re-connecting with working login credentials. "
            "If your credentials are active but we're still unable to establish a connection, "
            "please let us know by replying to this email.<br><br>"
        ),
    },
}


class RunStatus(BaseChoice):
    """
    Simple states describing statuses of runs
    CREATED: Run that's created in the DB, but not scheduled on an async task system yet
    SCHEDULED: Run that's scheduled, but not yet started
    STARTED: Started (given to the WebEDI workers)
    SUCCEEDED: Finished successfully
    FAILED: Finished with failure
    PARTIALLY_SUCCEEDED: Run partially succeeded
    """

    CREATED = (0, "Created")
    SCHEDULED = (1, "Scheduled")
    STARTED = (2, "Started")
    SUCCEEDED = (3, "Succeeded")
    FAILED = (4, "Failed")
    CANCELED = (5, "Canceled")
    PARTIALLY_SUCCEEDED = (6, "Partially succeeded")


class RunCancellationReason(BaseChoice):
    """
    Reasons describing why certain reason was cancelled.
    SCHEDULED_TIMED_OUT: This run was scheduled but wasn't run, so was cancelled
    SCHEDULED_MULTIPLE: Multiple runs were scheduled for this connection.
    This run was canceled to prevent duplicate sync.
    STARTED_TIMED_OUT: This run took too long and timed out
    STAFF_CANCELED: This run was manually canceled by Plate IQ staff
    CUSTOMER_CANCELED: This run was manually canceled by the customer
    """

    SCHEDULED_TIMED_OUT = (
        "scheduled-timed-out",
        "Run was scheduled but wasn't run, so was cancelled",
    )
    SCHEDULED_MULTIPLE = (
        "scheduled-multiple",
        "Multiple runs were scheduled for this connection",
    )
    STARTED_TIMED_OUT = ("started-timed-out", "Run took too long and timed out")
    STAFF_CANCELED = ("staff-canceled", "Run was manually canceled by Plate IQ staff")
    CUSTOMER_CANCELED = (
        "customer-canceled",
        "Run was manually canceled by the customer",
    )


class RunCreatedVia(BaseChoice):
    """
    Ways describing how runs are getting created.
    BATCH_PROCESS: This run was created by batch process
    ON_DEMAND: This run was created on demand, using admin panel
    """

    SCHEDULED = ("scheduled", "Scheduled run")
    CUSTOMER_REQUEST = ("customer", "Requested by customer")
    ADMIN_REQUEST = ("admin", "Via admin panel")


class InvalidStatusForOperation(Exception):
    """Raised when an operation is not permitted in a Run's current status"""


@model_prefix("run")
class Run(BaseModel):
    """
    Each individual run for Job jobconfig.
    :ivar Job job: Mandatory, job
    :ivar int status: Run Status
    :ivar datetime.datetime execution_start_ts: Execution start time
    :ivar datetime.datetime execution_end_ts: Execution end time
    :ivar datetime.datetime param_start_date: Parameter for execution: start date to look for documents
    :ivar datetime.datetime param_end_date: Parameter for execution: end date to look for documents
    :ivar request_parameters: Request Parameters for execution for Vendor & Accounting type as of now

    """

    job = models.ForeignKey(
        Job, null=False, related_name="runs", on_delete=models.PROTECT
    )
    action = CharChoiceField(
        choices=ConnectorCapabilityTypes, max_length=256, null=False
    )
    created_via = CharChoiceField(
        choices=RunCreatedVia,
        max_length=256,
        null=False,
        default=RunCreatedVia.SCHEDULED,
    )
    is_manual = models.BooleanField(null=False, default=False)
    request_parameters = JSONField(null=False, default=dict)
    dry_run = models.BooleanField(null=False, default=False)

    # Execution specific metadata
    status = models.IntegerField(
        null=False, choices=RunStatus.as_tuples(), default=RunStatus.CREATED.ident
    )
    execution_end_ts = models.DateTimeField(null=True)
    execution_start_ts = models.DateTimeField(null=True)
    aws_batch_job_id = models.TextField(null=True, blank=True, default=None)

    # only applicable if Run failed
    failure_issue = models.OneToOneField(
        Issue,
        null=True,
        default=None,
        related_name="failed_run",
        on_delete=models.SET_NULL,
    )
    canceled_reason = CharChoiceField(
        choices=RunCancellationReason,
        max_length=256,
        null=True,
        default=None,
    )
    canceled_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="run_canceled",
    )
    canceled_reason_text = models.TextField(null=True, blank=True, default=None)

    class Meta:
        indexes = [
            models.Index(fields=["created_date"]),
            models.Index(fields=["job"]),
            models.Index(fields=["status"]),
            models.Index(fields=["created_via"]),
        ]

    COMPLETED_STATES = (
        RunStatus.SUCCEEDED.ident,
        RunStatus.PARTIALLY_SUCCEEDED.ident,
        RunStatus.FAILED.ident,
        RunStatus.CANCELED.ident,
    )

    COMPLETED_STATES_WITH_CANCELED = COMPLETED_STATES + (RunStatus.CANCELED.ident,)

    @property
    def aws_batch_job_logs_link(self) -> Optional[str]:
        """
        Compute and return (if possible) the link to the relevant AWS Cloudwatch event log stream
        for this particular Run.

        WARNING: DO NOT USE IN LIST VIEWS, THIS WILL SLOW DOWN THE UI !
        """
        if not self.aws_batch_job_id:
            return f"None (aws_batch_job_id not set)"

        try:
            response = settings.AWS_BATCH_CLIENT.describe_jobs(
                jobs=[self.aws_batch_job_id]
            )
        except Exception as exc:  # pylint: disable=broad-except
            LOGGER.exception(
                f"[tag:WARMRABJL10][job:{self.job_id}][run:{self.id}]"
                f" Error while trying to describe job {self.aws_batch_job_id}: {exc}"
            )
            return f"None (describe_jobs raised exception '{exc}')"

        if (
            not isinstance(response, dict)
            or not response.get("ResponseMetadata")
            or response["ResponseMetadata"].get("HTTPStatusCode") != 200
            or not response.get("jobs")
        ):
            LOGGER.warning(
                f"[tag:WARMRABJL20][job:{self.job_id}][run:{self.id}] Unexpected response: {response}"
            )
            return "None (describe_jobs returned unexpected response)"

        stream_name = response["jobs"][0]["container"].get("logStreamName")
        if not stream_name:
            return f"None (describe_jobs response missing logStreamName - AWS Batch job has likely not run yet)"

        prefix = "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/"
        log_group = "/aws/batch/job".replace("/", "$252F")
        stream = stream_name.replace("/", "$252F")

        return f"{prefix}{log_group}/log-events/{stream}"

    @property
    def is_success(self):
        return self.status in (
            RunStatus.SUCCEEDED.ident,
            RunStatus.PARTIALLY_SUCCEEDED.ident,
        )

    def is_failed(self):
        return self.status == RunStatus.FAILED.ident

    def is_older_than(self, hours):
        return self.created_date < timezone.now() - timedelta(hours=hours)

    def _raise_if_already_complete(self, completed_states):
        if self.status in completed_states:
            raise ValidationError(f"Can't update already complete Run: {self.id}")

    def record_execution_start(self):
        if not LOCAL_ENV and self.status not in (
            RunStatus.CREATED.ident,
            RunStatus.SCHEDULED.ident,
        ):
            raise InvalidStatusForOperation(
                f"Can only start execution for runs in CREATED or SCHEDULED "
                f"states, current status is {self.status}"
            )

        LOGGER.info(f"Executing run {self.id}")
        self.execution_start_ts = timezone.now()
        self.status = RunStatus.STARTED.ident
        self.save()

    def record_success(self):
        """Mark run as successful and save to DB"""
        self._raise_if_already_complete(self.COMPLETED_STATES)
        self.status = RunStatus.SUCCEEDED.ident
        self.execution_end_ts = timezone.now()
        self.save()
        self.__notify_initial_success()
        LOGGER.info(f"Run: {self.id} Successfully completed.")

    def record_partial_success(self):
        """Mark run as partially succeeded and save to DB"""
        self._raise_if_already_complete(self.COMPLETED_STATES)
        self.status = RunStatus.PARTIALLY_SUCCEEDED.ident
        self.execution_end_ts = timezone.now()
        self.save()
        LOGGER.info(f"Run: {self.id} completed with partial success.")

    def __notify_initial_success(self):
        if self.job.connector.type != ConnectorType.VENDOR.ident:
            return

        if self.is_initial_run():
            from apps.runs import (  # pylint: disable=import-outside-toplevel,cyclic-import
                tasks,
            )

            tasks.send_email.delay(self.get_email_content("initial-success"))

    def get_email_content(self, state):
        return {
            "to_email": self.job.get_created_user_email(),
            "subject": EMAIL_TEMPLATES[state]["subject"].format(
                connector_name=self.job.connector.name
            ),
            "content": EMAIL_TEMPLATES[state]["content"].format(
                first_name=self.job.created_user.first_name,
                username=self.job.username,
                connector_name=self.job.connector.name,
            ),
        }

    def record_failure(self, exception: Exception = None):
        """Mark run as failed and save to DB"""
        self._raise_if_already_complete(self.COMPLETED_STATES)

        issue = Issue.build_from_exception(exception)
        with transaction.atomic():
            if issue:
                issue.save()
                self.failure_issue = issue

            self.status = RunStatus.FAILED.ident
            self.execution_end_ts = timezone.now()
            self.save()

        self.__notify_for_initial_failure()
        LOGGER.info(f"[run:{self.id}] Execution failed (exc: {exception})")

    def __notify_for_initial_failure(self):
        if self.job.connector.type != ConnectorType.VENDOR.ident:
            return

        from apps.runs import (  # pylint: disable=import-outside-toplevel,cyclic-import
            tasks,
        )

        if self.is_initial_run():
            tasks.send_email.delay(self.get_email_content("initial-failure"))
            return

        last_runs = self.job.runs.order_by("-created_date").all()[:2]
        if last_runs and len(last_runs) > 1:
            last_run = last_runs[1]
            if last_run.status == RunStatus.SUCCEEDED.ident:
                if (
                    self.failure_issue
                    and self.failure_issue.code
                    == ErrorCode.AUTHENTICATION_FAILED_WEB.ident
                ):
                    tasks.send_email.delay(self.get_email_content("credential-issue"))
                else:
                    tasks.send_email.delay(
                        self.get_email_content("operational-failure")
                    )

    def cancel(
        self, cancel_reason: RunCancellationReason, cancel_reason_text: str, canceled_by
    ):
        LOGGER.info(
            f"[run:{self.id}] Received cancellation request from {canceled_by} "
            f"(reason: {cancel_reason}, text: {cancel_reason_text})"
        )
        self._raise_if_already_complete(self.COMPLETED_STATES_WITH_CANCELED)
        self.status = RunStatus.CANCELED.ident

        if not self.execution_end_ts:
            self.execution_end_ts = timezone.now()
        self.canceled_reason = cancel_reason
        self.canceled_reason_text = cancel_reason_text
        self.canceled_by_user = canceled_by
        self.save()
        LOGGER.info(f"[run:{self.id}] Canceled run successfully")

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self._validate_insert_constraints()
        self._validate_execution_end_ts_if_complete()

        return super().save(force_insert, force_update, using, update_fields)

    def _validate_insert_constraints(self):
        if not self.pk:
            if self.status != RunStatus.CREATED.ident:
                raise ValidationError("Can only create new runs with CREATED status")

            if not self.job.connector.enabled:
                raise ValidationError("Can only create new runs for enabled Connectors")

    def _validate_execution_end_ts_if_complete(self):
        if (
            not self.execution_end_ts
            and self.status in self.COMPLETED_STATES_WITH_CANCELED
        ):
            raise ValidationError(
                f"execution_end_ts is mandatory for recording success/failure (Run id={self.id})"
            )

    def execute_async(self, force=False, on_demand=False):
        """
        Submit Run for asynchronous processing
        """
        if self.is_manual:
            return None

        is_retry = self.status in (
            RunStatus.SCHEDULED.ident,
            RunStatus.SUCCEEDED.ident,
            RunStatus.FAILED.ident,
        )
        if is_retry and not force:
            LOGGER.info(
                f"Ignoring requested re-submit for run: {self.id}, current status is {self.status}"
            )
            return None

        job_id = None
        from apps.runs import (  # pylint: disable=import-outside-toplevel,cyclic-import
            tasks,
        )

        has_task_time_limit = self._custom_properties_has_property(
            SupportedCustomProperties.CELERY_TASK_TIME_LIMIT
        )
        if has_task_time_limit:
            time_limit = has_task_time_limit.get("time_limit")
            soft_time_limit = has_task_time_limit.get("soft_time_limit")
            if on_demand:
                tasks.execute_run_on_demand.apply_async(
                    [self.id], soft_time_limit=soft_time_limit, time_limit=time_limit
                )
            else:
                if settings.RUN_SUBMIT_TO_AWS_BATCH:
                    job_id = self.__submit_aws_batch_job()
                else:
                    tasks.execute_run.apply_async(
                        [self.id],
                        soft_time_limit=soft_time_limit,
                        time_limit=time_limit,
                    )
        else:
            if on_demand:
                tasks.execute_run_on_demand.delay(self.id)
            else:
                if settings.RUN_SUBMIT_TO_AWS_BATCH:
                    job_id = self.__submit_aws_batch_job()
                else:
                    tasks.execute_run.delay(self.id)

        if not is_retry:
            self._transition_state_to_scheduled()

        return job_id

    def _custom_properties_has_property(self, custom_property):
        conn_custom_prop = self.job.connector.get_custom_properties.get(
            custom_property.ident
        )
        job_custom_prop = self.job.get_custom_properties.get(custom_property.ident)
        if job_custom_prop:
            return job_custom_prop
        if conn_custom_prop:
            return conn_custom_prop

        return None

    def __submit_aws_batch_job(self) -> Optional[str]:
        LOGGER.info(f"Submitting run: {self.id}")
        command = ["python3", "manage.py", "crawl", "--run_id", str(self.id)]

        container_overrides = {
            "command": command,
            "environment": [
                {"name": "ENV_CONFIG", "value": os.environ.get("ENV_CONFIG")},
                {"name": "APP_NAME", "value": settings.APP_NAME},
            ],
        }
        for env_var in ("SERVER_CONFIG", "WEBEDI_ENVIRONMENT"):
            if os.environ.get(env_var):
                container_overrides["environment"].append(
                    {"name": env_var, "value": os.environ.get(env_var)}
                )

        response = settings.AWS_BATCH_CLIENT.submit_job(
            jobName=f"{settings.APP_NAME}-crawl-{self.id}",
            jobDefinition="webedi-command:16",
            jobQueue="webedi-batch-jobs",
            containerOverrides=container_overrides,
        )
        LOGGER.info(f"Submitted run: {self.id}")
        with transaction.atomic():
            self.aws_batch_job_id = response.get("jobId")
            self.save()
        return self.aws_batch_job_id

    def _transition_state_to_scheduled(self):
        original_status = self.status
        if original_status != RunStatus.CREATED.ident:
            raise ValidationError(
                f"Can not move Run from status {original_status} to {RunStatus.SCHEDULED.ident}"
            )
        self.status = RunStatus.SCHEDULED.ident
        self.save()
        LOGGER.debug(
            f"Run Status Transitioned ({self.id}): {original_status} to {RunStatus.SCHEDULED.ident}"
        )

    def duplicate(self, **overrides) -> "Run":
        """
        Create a new Run with the same parameters and return the new one
        """
        run = Run.objects.create(
            job=self.job,
            action=self.action,
            created_via=overrides.get("created_via", self.created_via),
            is_manual=overrides.get("is_manual", self.is_manual),
            request_parameters=overrides.get(
                "request_parameters", self.request_parameters
            ),
            dry_run=overrides.get("dry_run", self.dry_run),
        )
        return run

    def reset(self):
        self.status = RunStatus.CREATED.ident
        self.execution_start_ts = None
        self.execution_end_ts = None
        self.save(force_update=True)

    def is_initial_run(self):
        return bool(self.request_parameters.get("suppress_invoices", False))

    def __str__(self):
        return f"{self.id}"


class FileFormat(BaseChoice):
    UNKOWN = ("unknown", "unknown")
    PDF = ("pdf", "pdf")
    CSV = ("csv", "csv")
    XLS = ("xls", "xls")
    JSON = ("json", "json")
    XML = ("xml", "xml")


class PaymentStatus(BaseChoice):
    PENDING = ("pending", "Pending")
    SUCCESS = ("success", "Success")
    FAILED = ("failed", "Failed")
    PROCESSED = ("processed", "Processed")


@model_prefix("discfile")
class DiscoveredFile(SoftDeleteModel):
    """
    Each individual file that was discovered as a part of a run. Note that discovered file does not necessarily
    mean downloaded. Examples of such cases would be:
        - A connector crawler finds a list of file urls when parsing the page, but one of them does not actually
          download but instead results in a 4xx or 5xx error because of connector error
        - A run execution crashes mid-way because of a bug. We ideally want to save everything we can as soon as
          possible to be as immune to such crashes as possible.
    :ivar Connector connector: Mandatory
    :ivar Run run: Mandatory, run
    :ivar str url: The S3 storage url for this file
    :ivar str reference_code: An id/code that UNIQUELY identifies this file PER VENDOR CONNECTOR.
                              Set to `None` if no such value is available.
    :ivar str original_filename: The name of the original file
    :ivar str original_download_url: The link of the file on the vendor connector, from which this file was downloaded
    :ivar str file_format: file format (pdf, json, csv, etc)
    :ivar str content_hash: hash of the file contents (to be used to deduplicate files, etc)
    :ivar str extracted_text_hash: hash of the text extracted from file (to be used to deduplicate files, etc)
    :ivar str collision_dedupe: this will be used when content-hash is happened to be same for two different files.
    :ivar datetime.datetime downloaded_at: When was the file downloaded
    :ivar bool downloaded_successfully: Was this file downloaded successfully? This field ALLOWS NULL values.
                    This is 3 valued logic. NULL means download not attempted. TRUE means downloaded successfully.
                    FALSE means download failed.
    :ivar str document_type: Which document is it? (invoice, statement), etc
    :ivar str document_properties: Additional, optional properties related to this file/document
    """

    connector = models.ForeignKey(
        Connector, null=False, related_name="discovered_files", on_delete=models.PROTECT
    )
    run = models.ForeignKey(
        Run, null=False, related_name="discovered_files", on_delete=models.PROTECT
    )
    url = models.TextField(null=True, default=None)
    original_file = models.FileField(
        storage=storage_utils.get_s3_storage(
            settings.INTEGRATOR_BUCKET,
            location="discovered_files/original",
            querystring_auth=True,
        ),
        max_length=512,
        null=True,
        blank=True,  # we don't populate upload_to because storage.location covers it
    )
    original_filename = models.TextField(null=False, blank=False)
    original_download_url = models.TextField(null=False, blank=True)
    file_format = models.TextField(
        null=False,
        blank=False,
        choices=FileFormat.as_tuples(),
        default=FileFormat.UNKOWN.ident,
    )
    content_hash = models.CharField(
        null=False,
        blank=True,
        max_length=128,
        default=None,
        validators=[validate_not_blank_string__allow_null],
    )
    extracted_text_hash = models.CharField(
        null=True,
        blank=True,
        max_length=128,
        default=None,
        validators=[validate_not_blank_string__allow_null],
    )
    collision_dedupe = models.TextField(null=False, blank=True, default="")

    downloaded_successfully = models.BooleanField(null=True, default=None)
    downloaded_at = models.DateTimeField(null=True)

    document_type = models.TextField(
        null=False, blank=False, choices=DocumentType.as_tuples()
    )
    document_properties = JSONField(null=False, default=dict)
    # below fields are for logging purposes, for further processing we send it to EDI,
    # for that process we need following columns. Microwave(iternal service)-digital pdf parse
    piq_upload_id = models.CharField(null=True, blank=True, max_length=50, default=None)
    piq_container_id = models.CharField(
        null=True, blank=True, max_length=50, default=None
    )

    class Meta:
        unique_together = [
            ("content_hash", "collision_dedupe"),
            ("extracted_text_hash", "collision_dedupe"),
        ]

    class AlreadyExists(Exception):
        """Exception to be thrown when tryign to create"""

        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_filepath: Optional[str] = None

    @property
    def discovery_action(self) -> Optional[FileDiscoveryAction]:
        """Returns the FileDiscoveryAction applicable to this Discovered File"""
        job = self.run.job

        discovery_action: FileDiscoveryAction = job.document_discovery_actions.filter(
            document_type=self.document_type
        ).first()

        if not discovery_action:
            # check connector default
            discovery_action: FileDiscoveryAction = (
                self.connector.document_discovery_actions.filter(
                    document_type=self.document_type
                ).first()
            )
        return discovery_action

    @property
    def discovery_action_for_admin(self) -> Optional[FileDiscoveryAction]:
        """Returns the FileDiscoveryAction applicable to this Discovered File"""
        job = self.run.job
        connector = self.connector
        conn_discovery_action = None
        job_discovery_action = job.document_discovery_actions.all()
        job_discovery_action = list(
            filter(
                lambda x: x.document_type == self.document_type, job_discovery_action
            )
        )
        job_discovery_action = job_discovery_action[0] if job_discovery_action else None

        if not job_discovery_action:
            conn_discovery_action = connector.document_discovery_actions.all()
            conn_discovery_action = list(
                filter(
                    lambda x: x.document_type == self.document_type,
                    conn_discovery_action,
                )
            )
            conn_discovery_action = (
                conn_discovery_action[0] if conn_discovery_action else None
            )

        return job_discovery_action or conn_discovery_action

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self.connector = self.run.job.connector
        super().save(force_insert, force_update, using, update_fields)

    def save_content(self, local_filepath, compute_extracted_text_hash=True):
        """
        Unified method to compute and save the appropriate fields in DF
        :param local_filepath: Path to local file that is to be saved
        :param compute_extracted_text_hash: Whether or not to compute and save
                                            extracted_text_hash
        :return:
        """
        if self.pk:
            raise Exception(
                f"[df:{self.pk}] save_content is intended for files that"
                f"have not been created in the DB yet"
            )
        if not local_filepath or not os.path.exists(local_filepath):
            raise Exception(
                f"Can't save file contents if there's no local file: {local_filepath}"
            )

        content_hash, extracted_text_hash = self.compute_hashes(
            local_filepath, compute_extracted_text_hash
        )

        self.content_hash = content_hash
        self.extracted_text_hash = extracted_text_hash
        self.save()

        # Lastly, upload df to s3 for permanent storage. Prefix is automatically added by storage
        ext = get_extension(local_filepath)
        filename = f"{self.id}.{ext}"
        with open(local_filepath, "rb") as file_contents:
            self.original_file.save(filename, file_contents, save=True)
        LOGGER.debug(f"[tag:WARMDFSC10] Uploaded to S3: {self.original_file}")

    @classmethod
    def compute_hashes(
        cls, local_filepath, compute_extracted_text_hash=True
    ) -> (str, str):
        # basic sanity checks
        if not local_filepath or not os.path.exists(local_filepath):
            return None, None

        # content_hash
        with open(local_filepath, "rb") as file_contents:
            content_hash = cls.get_content_hash_for_file(
                file_contents.read(), local_filepath
            )

        # extracted_text_hash
        extracted_text_hash = None
        if compute_extracted_text_hash and is_pdf(local_filepath):
            try:
                text = textract.process(local_filepath)
                if text == b"\x0c\x0c" or text == b"\x0c\x0c\x0c\x0c":
                    extracted_text_hash = ""
                else:
                    extracted_text_hash = cls.get_content_hash_for_file(text)
            except UnicodeDecodeError as exc:
                LOGGER.warning(
                    f"[tag:WARMDFETH30] Failed computing text hash "
                    f"for {local_filepath} with exception: {exc}."
                )
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.exception(
                    f"[tag:WARMDFETH20] Failed computing text hash "
                    f"for {local_filepath} with exception: {exc}."
                )

        return content_hash, extracted_text_hash

    @staticmethod
    def get_content_hash_for_file(file_contents, local_filepath=None):

        if not local_filepath:
            return hashlib.sha1(file_contents).hexdigest()

        file_extension = get_extension(local_filepath)
        if file_extension.lower() == "json":
            try:
                data = json.loads(file_contents)
                if data.get("meta").get("generator").get("execution_id"):
                    data.pop("meta")
                return hashlib.sha1(bytes(json.dumps(data), "utf-8")).hexdigest()
            except Exception as exc:
                raise Exception(
                    f"[tag:WARMDFETH40][{local_filepath}] Something went wrong while getting content hash "
                    f"for json file, exc : {exc}"
                )
        else:
            return hashlib.sha1(file_contents).hexdigest()

    @classmethod
    def build_unique(
        cls,
        run: Run,
        reference_code: str,
        *,
        document_type,
        file_format: str,
        original_download_url,
        original_filename,
        document_properties,
    ):
        """
        Returns either an existing DiscoveredFile matching a unique (connector+reference_code), or builds a new one.
        Raises if a discovered file from the same run exists
        """
        discovered_file = DiscoveredFile(run=run, document_type=document_type)
        discovered_file.file_format = file_format
        discovered_file.original_download_url = original_download_url
        discovered_file.original_filename = original_filename
        discovered_file.document_properties = document_properties
        return discovered_file

    def delete(self, using=None, keep_parents=False):
        # updating content hash, appending deleted
        if self.content_hash and "##deleted" not in self.content_hash:
            self.content_hash = (
                f"{self.content_hash}##{int(round(time.time()))}##deleted"
            )
        super().delete(self)

    @property
    def file_url(self):
        if self.original_file:
            _url = self.original_file.url
        elif self.url:
            _url = self.url
        else:
            _url = None
        return _url


class CheckRunExists(ContextualError):
    """Raised if trying to create a CheckRun that already exists"""

    def __init__(self, previous_checkrun: "CheckRun"):
        super().__init__(
            ErrorCode.PE_CHECKRUN_ALREADY_EXISTS.ident,
            ErrorCode.PE_CHECKRUN_ALREADY_EXISTS.message,
        )
        self.previous_checkrun = previous_checkrun


class CheckRunDisabled(Exception):
    """Raised if trying to create a CheckRun for disabled check run id"""

    def __init__(self, previous_checkrun: "CheckRun"):
        super().__init__(
            f"Check run {previous_checkrun.id} is disabled, hence skipping"
        )
        self.previous_checkrun = previous_checkrun


@model_prefix("chrun")
class CheckRun(BaseModel):
    """
    For any manual payment update in Accounting website, this model is updated with relevant details.
    :ivar Connector connector: Mandatory
    :ivar Run run: Mandatory, run
    :ivar int check_run_id: Unique Check Run ID for every Bill Pay Payment
    :ivar bool is_checkrun_success: True in case Payment is updated in Accounting Connector else False
    :ivar bool is_patch_success: True in case Billpay Check Payment is marked as Exported else False
    """

    run = models.ForeignKey(
        Run, null=False, related_name="check_runs", on_delete=models.PROTECT
    )

    check_run_id = models.IntegerField(null=True, blank=False, default=None)
    is_checkrun_success = models.BooleanField(null=True, default=None)
    is_patch_success = models.BooleanField(null=True, default=None)
    is_disabled = models.BooleanField(null=True, default=None)

    manual_exporter_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="manually_exported_check_runs",
    )

    # only applicable if CheckRun failed
    failure_issue = models.OneToOneField(
        Issue,
        null=True,
        default=None,
        related_name="failed_checkrun",
        on_delete=models.SET_NULL,
    )

    class Meta:
        unique_together = [
            ("run_id", "check_run_id"),
        ]

    @classmethod
    def create_unique(cls, run: Run, check_run_id: int):
        """Creates a check"""
        connector = run.job.connector

        if previous_checkrun := cls.get_previous_successful_checkrun(
            connector, check_run_id
        ):
            LOGGER.warning(
                f"Checkrun {check_run_id} ({connector.id}) has already been processed successfully"
            )
            raise CheckRunExists(previous_checkrun)

        disabled_check_runs = cls.objects.filter(
            is_disabled=True, check_run_id=check_run_id
        ).first()
        if disabled_check_runs:
            LOGGER.warning(f"Checkrun {check_run_id} ({connector.id}) is disabled.")
            raise CheckRunDisabled(disabled_check_runs)

        if previous_checkrun := cls.get_previous_successful_checkrun_with_failed_patch(
            connector, check_run_id
        ):
            LOGGER.warning(
                f"Checkrun {check_run_id} ({connector.id}) has already been exported successfully,"
                f" but patch has failed"
            )
            raise CheckRunExists(previous_checkrun)

        checkrun = cls(run=run, check_run_id=check_run_id)
        checkrun.save()
        return checkrun

    @classmethod
    def get_previous_successful_checkrun(
        cls, connector: Connector, check_run_id: int
    ) -> "CheckRun":
        """
        Returns true if previous successful (connector+check_run_id) exist
        where is_checkrun_success=True
                AND is_patch_success=True
        False otherwise.
        """
        return (
            cls.objects.filter(
                run__job__connector=connector,
                check_run_id=check_run_id,
                is_checkrun_success=True,
            )
            .filter(is_patch_success=True)
            .order_by("-created_date")
            .first()
        )  # ideally there would only be one, but manual updates might mess with that assumption.

    @classmethod
    def get_previous_successful_checkrun_with_failed_patch(
        cls, connector: Connector, check_run_id: int
    ) -> "CheckRun":
        """
        Returns true if previous (connector+check_run_id) exist
        where is_checkrun_success=True
                AND is_patch_success is not True
        False otherwise.
        """
        return (
            cls.objects.filter(
                run__job__connector=connector,
                check_run_id=check_run_id,
                is_checkrun_success=True,
            )
            .exclude(is_patch_success=True)
            .order_by("-created_date")
            .first()
        )  # ideally there would only be one, but manual updates might mess with that assumption.

    def mark_as_manually_exported(self, manual_exporter_user: AbstractUser):
        """
        Manually mark this CheckRun as completely processed.
        This will only work if the export hasn't already been marked as exported

        :param manual_exporter_user: User who is manually marking this as exported
        """
        if self.is_checkrun_success:
            LOGGER.warning(
                f"CheckRun {self.id} (chequerun_id:{self.check_run_id}) is already exported,"
                f" ignoring attempt to re mark it"
            )
            return

        with transaction.atomic():
            self.is_checkrun_success = True
            self.manual_exporter_user = manual_exporter_user
            self.save()

        self.notify_export_success()

    def notify_export_success(self):
        """Notify that PIQ Backend that this CheckRun was successfully exported"""
        if not self.is_checkrun_success:
            raise ValidationError(
                f"CheckRun {self.id} (chequerun_id:{self.check_run_id}) is not exported successfully,"
                f" can't mark it as exported in PIQ Backend"
            )

        patch_response = settings.PIQ_CORE_CLIENT.billpay_export_patch(
            [self.check_run_id]
        )
        self.is_patch_success = bool(patch_response)
        self.save()

    def record_export_success(self):
        """Mark checkrun export as successful and save to DB"""
        LOGGER.info(f"[tag:WERMCRREF10][checkrun:{self.id}] Recording export success")
        self.is_checkrun_success = True
        self.save()

    def record_export_failure(self, exception: Exception = None):
        """Mark checkrun export as failed and save to DB"""
        LOGGER.info(f"[tag:WERMCRREF10][checkrun:{self.id}] Recording export failure")

        issue = Issue.build_from_exception(exception)
        with transaction.atomic():
            if issue:
                issue.save()
                self.failure_issue = issue

            self.is_checkrun_success = False
            self.save()

    def mark_disabled(self):
        self.is_disabled = True
        self.save()

    def mark_not_disabled(self):
        self.is_disabled = False
        self.save()


@model_prefix("exreq")
class ExportRequest(BaseModel):
    """
    Represents each unique export request made to Core Backend

    :ivar Run run: which run is this request data coming from

    :ivar str http_request_method: HTTP request method
    :ivar str http_request_url: HTTP request URL
    :ivar dict http_request_json: HTTP request json body
    :ivar int http_response_code: HTTP response code
    :ivar str http_response_body: HTTP response body
    """

    run = models.ForeignKey(
        Run, null=False, related_name="export_requests", on_delete=models.PROTECT
    )

    http_request_method = models.CharField(null=False, max_length=10)
    http_request_url = models.TextField(null=False)
    http_request_json = JSONField(null=True)

    http_response_code = models.IntegerField(null=True, default=None)
    http_response_body = models.TextField(null=True, default=None)

    success = models.BooleanField(null=True, default=None)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if self.http_response_code is not None and self.success is None:
            if 200 <= self.http_response_code < 300:
                self.success = True
            else:
                self.success = False

        return super().save(force_insert, force_update, using, update_fields)


@model_prefix("discentt")
class DiscoveredEntity(BaseModel):
    """
    Represents each individual entity that was discovered as a part of a run.

    Unlike DiscoveredFile, these entities ARE NOT UNIQUE PER CONNECTOR, only per run. The reason for this
    is that current use cases do not require deduplication. When we require deduplication, we can design for it.

    :ivar Connector connector: the source connector from which the object is discovered
    :ivar Run run: the run during which this was discovered
    :ivar str type: Type of the entity
    :ivar int attrs: Attributes about the entity. Each entity type has its fixed set of attrs.
    :ivar str source_entity_id: What is the source connector's primary key for this particular entity object?
    """

    run = models.ForeignKey(
        Run, null=False, related_name="discovered_entities", on_delete=models.PROTECT
    )
    type = models.CharField(null=False, choices=EntityType.as_tuples(), max_length=100)
    attrs = JSONField(null=False)
    source_entity_id = models.CharField(null=True, max_length=100)

    export_request = models.ForeignKey(
        ExportRequest,
        null=True,
        default=None,
        related_name="discovered_entities",
        on_delete=models.PROTECT,
    )

    class Meta:
        unique_together = [("run", "type", "source_entity_id")]


@model_prefix("vndrpmt")
class VendorPayment(BaseModel):
    """
    Each payment that was done as per invoice information as a part of a run. Examples of such cases would be:
        - A connector crawler finds a list of invoices when parsing the page, but one of them does not actually
          pay but instead results in a 4xx or 5xx error because of connector error
        - A run execution crashes mid-way because of a bug. We ideally want to save everything we can as soon as
          possible to be as immune to such crashes as possible.
    :ivar Run run: Mandatory, run
    :ivar str payment_status: what is status of payment? (success, failed, processed), etc
    :ivar str payment_details: Additional, optional properties related to this payment
    """

    run = models.ForeignKey(
        Run, null=False, related_name="vendor_payments", on_delete=models.PROTECT
    )
    payment_status = TextChoiceField(
        null=False,
        blank=False,
        choices=PaymentStatus,
        default=PaymentStatus.PENDING.ident,
    )
    payment_details = JSONField(null=True, default=None)
    failure_issue = models.OneToOneField(
        Issue,
        null=True,
        default=None,
        related_name="failed_payment",
        on_delete=models.SET_NULL,
    )


# move to spices
def is_pdf(filename: str) -> bool:
    """Returns true if the given file's extension is PDF, False otherwise"""
    return get_extension(filename).lower() == "pdf"


def get_extension(filename: str) -> str:
    """Returns the file's extension, without the preceding dot"""
    return os.path.splitext(filename)[1][1:]
