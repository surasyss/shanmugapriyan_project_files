import calendar
import datetime
from datetime import timedelta
from typing import Optional

import time
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import UniqueConstraint, Q
from django.utils import timezone
from django_better_admin_arrayfield.models.fields import ArrayField

from apps.definitions.models import Connector, ConnectorType, ConnectorCapabilityTypes
from apps.jobconfig import LOGGER
from spices.django3 import thread_local
from spices.django3.base_model.models import (
    BaseModel,
    model_prefix,
    SoftDeleteModel,
    SoftDeleteManager,
)
from spices.django3.coreobjects.base import SharedCoreObjectModel
from spices.django3.credentials.models import FTPCredential
from spices.django3.fields import EncryptedTextField, CharChoiceField, PrefixedIdField
from spices.documents import DocumentType
from spices.enum_utils import BaseChoice


class EDIType(BaseChoice):
    _810 = ("810", "810")
    PIQ = ("piq", "PlateIQ")
    PIQ_JSON = ("piq_json", "PlateIQ JSON Invoice Format")
    FINTECH = ("fintech", "Fintech")
    BALDOR = ("baldor", "Baldor")
    BERGIN = ("bergin", "Bergin")
    SINGER = ("singer", "Singer")
    STAPLES = ("staples", "Staples")
    USFOODS = ("us_foods_webedi", "USFoods (WebEDI)")
    SERVICECHANNEL = ("service_channel", "ServiceChannel")
    AMAZON = ("amazon", "Amazon")
    FEDEX = ("fedex", "Fedex")
    WESTCOAST = ("westcoast", "WestCoast")
    BENKEITH = ("benkeith", "Ben E. Keith")
    RESTAURANT_DEPOT = ("restaurant_depot_webedi", "Restaurant Depot (WebEDI)")
    DOORDASH = ("doordash_webedi", "DoorDash (WebEDI)")
    DOORDASH_CAVA = ("doordash_cava", "DoorDash Cava (WebEDI)")
    TXU = ("txu_webedi", "TXU Energy (WebEDI)")
    LOOMIS_TORCHYS = ("loomis_torchys", "Loomis Torchys")
    NWA_TORCHYS = ("nationalwaste_torchys", "National Waste Torchys")
    FUZE_CAVA = ("fuze_cava", "Fuze Cava")
    SMART_FOOD_SERVICE = (
        "smart_food_service",
        "Smartfood Service (formerly Cash&Carry)",
    )
    ENTERPRISE_FM = ("enterprise_fleet_management", "Enterprise Fleet Management")
    SYSCO = ("sysco_webedi", "Sysco (WebEDI)")
    EDI_820 = ("EDI_820", "EDI_820")


class JobDisabledReason(BaseChoice):
    INCORRECT_CREDENTIALS = ("incorrect-credentials", "Incorrect credentials")
    ACCOUNT_DISABLED = ("account-disabled", "The vendor has disabled this user account")
    MFA_ENABLED = ("mfa-enabled", "Multi Factor Authentication enabled")
    REQUIRES_PASSWORD_UPDATE = ("requires-password-update", "Requires Password Update")
    OTHER = ("other", "Other")


class JobManager(SoftDeleteManager):
    def runnable(self, operation: ConnectorCapabilityTypes = None):
        queryset = (
            super()
            .get_queryset()
            .filter(enabled=True, connector__enabled=True)
            .exclude(connector__adapter_code="backlog")
        )

        if operation:
            if isinstance(operation, str):
                operation = ConnectorCapabilityTypes.from_ident(operation)

            if (
                operation
                is ConnectorCapabilityTypes.ACCOUNTING__IMPORT_MULTIPLE_ENTITIES
            ):
                operations = [
                    ConnectorCapabilityTypes.ACCOUNTING__IMPORT_MULTIPLE_ENTITIES,
                    ConnectorCapabilityTypes.BANK_ACCOUNT__IMPORT_LIST,
                    ConnectorCapabilityTypes.GL__IMPORT_LIST,
                    ConnectorCapabilityTypes.VENDOR__IMPORT_LIST,
                ]
            else:
                operations = [operation]

            queryset = queryset.filter(connector__capabilities__type__in=operations)

        queryset = queryset.distinct()
        return queryset

    def runnable__invoice_download__manual(self):
        return self.runnable(ConnectorCapabilityTypes.INVOICE__DOWNLOAD).filter(
            Q(enabled_for_manual=True) | Q(connector__adapter_code="manual")
        )

    def runnable__invoice_download__automated(self):
        return self.runnable(ConnectorCapabilityTypes.INVOICE__DOWNLOAD).exclude(
            connector__adapter_code="manual"
        )


@model_prefix("job")
class Job(SoftDeleteModel):
    """
    Represents mappings of (Connector+Credential) with for Plate IQ customers, optionally mapping with
    restaurant groups or individual restaurants. When WebEDI is productized such that customers can set up
    their own integrations, this would be the table from where customers would see the list of their current
    integrations, whether enabled or disabled.

    Constraints:
        - Connector + Credential is unique
        - if restaurant is specified, then (Connector + Credential + Restaurant) is unique

    Notes / Limitations:
        The biggest complexity here will come from mismatching hierarchies In the Plate IQ hierarchy, the only
        "real" things are Restaurant and Company (and company is not in consideration here so ignore that).
        RG and RA are imaginary.
        PIQ-RA may be different from Connector-RA. Connector-RA => for the Connector, one login represents one customer
        account (which may be able to see invoices for multiple RGs/Rs).
        In the current design, if we have cases where the PIQ RA is a SUPERSET of Connector-RAs, we're fine,
        because this table stores those mappings. However, if PIQ-RA is a subset of Connector-RA, that is,
        Example:
            - if PIQ-RA-1 contains {a, b,}
            - if PIQ-RA-2 contains {c}
            - and the Connector-RA login actually gives us access to {a,b,c,d}
            - then we will need some way of filtering out results for Restaurant d
            - this is a hard problem, deferred for later

    :ivar Connector connector: Connector.
    :ivar str username: KMS encrypted text field
    :ivar str password: KMS encrypted text field
    :ivar bool enabled: Whether this Connector is ready for use (can be only be enabled if Connector is enabled)

    :ivar Account account: Mandatory, Restaurant Account
    :ivar RestaurantGroup restaurant_group: Optional, restaurant groups to map to
    :ivar Restaurant restaurant: Optional, restaurant to map to
    :ivar List[Restaurant] candidate_restaurants: If restaurant is not set, set of candidate restaurants

    :ivar LastRun last_run:
    """

    objects = JobManager()

    connector = models.ForeignKey(
        Connector, null=False, related_name="jobs", on_delete=models.PROTECT
    )
    username = models.TextField(null=False, blank=False)

    password = EncryptedTextField(null=False)
    login_url = models.TextField(null=False, blank=True, default="")

    enabled = models.BooleanField(null=False, default=False)
    enabled_for_manual = models.BooleanField(null=False, default=False)
    disabled_reason = CharChoiceField(
        choices=JobDisabledReason, blank=True, null=True, max_length=128
    )
    disabled_reason_text = models.TextField(null=True, blank=True)
    disabled_at_date = models.DateTimeField(null=True, blank=True)
    disabled_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="job_disabled",
    )

    account = models.ForeignKey(
        SharedCoreObjectModel,
        related_name="account_jobs",
        null=False,
        blank=False,
        on_delete=models.PROTECT,
    )
    location_group = models.ForeignKey(
        SharedCoreObjectModel,
        related_name="location_group_jobs",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    location = models.ForeignKey(
        SharedCoreObjectModel,
        related_name="location_jobs",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    candidate_restaurant_ids = ArrayField(
        models.IntegerField(null=False, blank=False),
        null=True,
        blank=True,
        default=list,
    )
    companies = models.ManyToManyField(
        SharedCoreObjectModel, blank=True, related_name="company_jobs"
    )
    # Following columns are added for FTP Based EDI Job
    ftp_credential = models.ForeignKey(
        FTPCredential,
        related_name="jobs",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    create_missing_vendors = models.NullBooleanField(default=False)
    notes = models.TextField(max_length=500, blank=True, null=True)
    invoice_email = ArrayField(models.EmailField(max_length=256), blank=True, null=True)
    custom_properties = JSONField(
        null=True,
        default=None,
        blank=True,
    )

    @property
    def last_run(self):
        """Returns the last executed run"""
        return self.runs.order_by("-created_date").first()

    class Meta:
        unique_together = [
            # by definition
            (
                "connector",
                "username",
                "login_url",
            ),
        ]

    def is_active(self):
        """Consider it active only if it and all its parents are active"""
        return self.enabled and self.connector.enabled

    @property
    def requested_document_type(self) -> str:
        """What all document types are requested by this Job"""
        return "invoice"

    @property
    def requested_file_type(self) -> str:
        """What all file types are requested by this Job"""
        return "pdf"

    def delete(self, using=None, keep_parents=False):
        """Soft deleting the job with related discovered files"""
        # marking deleted discovered files of the job
        with transaction.atomic():
            # pylint: disable=import-outside-toplevel,cyclic-import
            from apps.runs.models import DiscoveredFile

            # pylint: enable=import-outside-toplevel,cyclic-import

            # deleting discovered file
            DiscoveredFile.objects.filter(run__job=self).delete()
            # Updating username for job
            if "##deleted" not in self.username:
                self.username = f"{self.username}##{int(round(time.time()))}##deleted"
            super().delete(self)

    def hard_delete(self, *, i_am_not_crazy: bool):
        if not i_am_not_crazy:
            raise ValidationError("Hard deleting job without confirmation is blocked")

        current_user = thread_local.get_current_request_user()
        LOGGER.warning(f"Hard deleting job {self.id} (requesting user: {current_user})")

        self.document_discovery_actions.all().delete()
        self.customer_number_mappings.all().delete()
        self.piq_mappings.all().delete()

        from apps.runs.models import (  # pylint: disable=import-outside-toplevel,cyclic-import
            DiscoveredFile,
        )

        DiscoveredFile.objects.filter(run__job=self).delete()
        self.runs.all().delete()
        self.delete()

    def __str__(self):
        account_name = self.account.display_name if self.account else "-"
        return f"{self.connector} - {account_name}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        # validating username or password change, if there is any change, updating disabled_reason as well.
        if self.pk:
            current_object = Job.objects.all_with_deleted().get(pk=self.pk)
            if (
                current_object.disabled_reason
                and current_object.disabled_reason
                == JobDisabledReason.INCORRECT_CREDENTIALS
            ):
                if (current_object.username != self.username) or (
                    current_object.password != self.password
                ):
                    self.disabled_reason = None
                    self.disabled_reason_text = None
        return super().save(force_insert, force_update, using, update_fields)

    def get_created_user_email(self):
        return self.created_user.email

    @property
    def get_custom_properties(self) -> dict:
        """custom properties for job"""
        return self.custom_properties or {}


class FileDiscoveryActionType(BaseChoice):
    """
    Choices of supported actions to be executed after discovery of a document - these may be document specific.
    """

    NONE = ("none", "Do nothing")
    PIQ_STANDARD_UPLOAD = ("piq_nonedi", "Upload to Plate IQ (non EDI Invoice)")
    PIQ_EDI_UPLOAD = ("piq_edi", "Upload to Plate IQ (EDI Invoice)")
    PAYMENTS_EDI_UPLOAD = ("payments_edi_upload", "Upload payments to EDI")


@model_prefix("fdact")
class FileDiscoveryAction(BaseModel):
    """
    Define what action must be taken after the discovery of a document, based on document type.

    If no record is found for a document type for a particular job, the default behavior will be
    the same as it would be if a record existed with action = NONE
    """

    job = models.ForeignKey(
        Job,
        null=True,
        related_name="document_discovery_actions",
        on_delete=models.PROTECT,
    )
    connector = models.ForeignKey(
        Connector,
        null=True,
        related_name="document_discovery_actions",
        on_delete=models.PROTECT,
    )
    document_type = models.TextField(
        null=False, blank=False, choices=DocumentType.as_tuples()
    )
    action_type = models.CharField(
        max_length=100,
        choices=FileDiscoveryActionType.as_tuples(),
        null=False,
        blank=False,
    )

    # piq specific
    edi_parser_code = models.CharField(
        max_length=100, choices=EDIType.as_tuples(), null=True, blank=True
    )

    class Meta:
        unique_together = [
            ("job", "document_type"),
            ("connector", "document_type"),
        ]

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if (not self.job_id and not self.connector_id) or (
            self.job_id and self.connector_id
        ):
            raise ValidationError("Exactly one of job or connector should be set")

        return super().save(force_insert, force_update, using, update_fields)


@model_prefix("piqmap")
class PIQMapping(BaseModel):
    """
    PIQ Mapping model is to mapping any type of data (eg. Location/Vendor/Acct etc) need to be mapped to entities in
    PIQ database & also support custom mappings.
    Generally the Restaurant names used in Vendor Portals differ from the Restaurant names in PIQ database.
    Also this mapping will help in moving the invoices to the exact restaurants
    Another use case is that these mappings will be used in payment export where sites eg. R365 have
    locations/vendor/bank_account names which differs from PIQ respective fields. In that case we want to mapped it to
    some custom fields instead mapping_data(sharedcoreobject)

    Constraints:
        - Job + piq_data(sharedCoreObject) + Friendly Name is unique

    :ivar Job job: Job
    :ivar int piq_data: SharedCoreObject in PIQ (eg. Location, Vendor, Acct etc
    :ivar mapping_data name: Friendly Name present in Connectors
    :ivar mapped_to: Optional custom field where mapping_data should be mapped to. This is additional field where we
          want to do custom mapping instead of mapping it with piq_data
    """

    job = models.ForeignKey(
        Job, null=False, related_name="piq_mappings", on_delete=models.PROTECT
    )
    piq_data = models.ForeignKey(
        SharedCoreObjectModel,
        related_name="scom_piq_mappings",
        null=False,
        blank=False,
        on_delete=models.PROTECT,
    )
    mapping_data = models.TextField(null=False, blank=False)
    mapped_to = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = [("job", "piq_data", "mapping_data")]

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if self.mapping_data:
            self.mapping_data = self.mapping_data.lower()
        return super().save(force_insert, force_update, using, update_fields)

    @classmethod
    def get_piq_mapped_data(
        cls, job: Job, mapping_field: str, mapping_type: str
    ) -> Optional[int]:
        piq_mapped_data = PIQMapping.objects.filter(
            job=job, mapping_data__iexact=mapping_field, piq_data__type=mapping_type
        ).first()
        if piq_mapped_data:
            return (
                int(piq_mapped_data.piq_data.remote_id)
                if piq_mapped_data.piq_data
                else None
            )
        return None

    def __str__(self):
        return f"{self.job}, {self.piq_data}, {self.mapping_data}"


@model_prefix("cnmap")
class CustomerMapping(BaseModel):
    job = models.ForeignKey(
        Job,
        null=False,
        blank=False,
        related_name="customer_number_mappings",
        on_delete=models.PROTECT,
    )
    location = models.ForeignKey(
        SharedCoreObjectModel,
        related_name="location_customer_number_mappings",
        null=False,
        blank=False,
        on_delete=models.PROTECT,
    )
    vendor = models.ForeignKey(
        SharedCoreObjectModel,
        null=True,
        blank=True,
        related_name="vendor_customer_number_mappings",
        on_delete=models.SET_NULL,
    )

    customer_number = models.CharField(max_length=128, null=False, blank=False)
    enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("job", "customer_number")

    def __str__(self):
        # pylint: disable=no-member
        return (
            f'{self.location.display_name} - {self.vendor.display_name if self.vendor else "None"} -> '
            f"{self.customer_number}"
        )


@model_prefix("conreq")
class ConnectorRequest(SoftDeleteModel):
    account = models.ForeignKey(
        SharedCoreObjectModel,
        related_name="account_connector_requests",
        on_delete=models.PROTECT,
    )
    type = CharChoiceField(choices=ConnectorType, max_length=50)
    name = models.TextField()
    login_url = models.TextField()
    username = models.TextField()
    password = EncryptedTextField(null=False, blank=True)

    converted_to_job = models.ForeignKey(
        Job, null=True, blank=True, default=None, on_delete=models.SET_NULL
    )
    converted_to_connector = models.ForeignKey(
        Connector, null=True, blank=True, default=None, on_delete=models.SET_NULL
    )

    def __str__(self):
        account_name = self.account.display_name if self.account else "-"
        return f"CR: {account_name} - {self.name}"

    def convert_to_job(self) -> Job:
        """Create job from connector request, and delete request"""
        job = Job.objects.filter(
            account_id=self.account_id,
            connector_id=self.converted_to_connector_id,
            username=self.username,
        ).first()
        if job and job.password == self.password:
            # Only consider them duplicates if the passwords match.
            # Otherwise we might lose something useful.
            self.delete()
            return job

        with transaction.atomic():
            job = Job()
            job.connector = self.converted_to_connector
            job.account = self.account
            job.username = self.username
            job.password = self.password
            job.enabled = True
            job.save()

            self.converted_to_job = job
            self.password = ""
            self.save()
            self.delete()

        return job


class Period(BaseChoice):
    DAY = ("day", "Day")
    WEEK = ("week", "Week")
    MONTH = ("month", "Month")
    FORTNIGHT = ("fortnight", "Fortnight")


class DaysOfWeek(BaseChoice):
    MONDAY = ("monday", "Monday")
    TUESDAY = ("tuesday", "Tuesday")
    WEDNESDAY = ("wednesday", "Wednesday")
    THURSDAY = ("thursday", "Thursday")
    FRIDAY = ("friday", "Friday")
    SATURDAY = ("saturday", "Saturday")
    SUNDAY = ("sunday", "Sunday")


class Frequency(BaseChoice):
    DAILY = ("daily", "Daily")
    WEEKLY = ("weekly", "Weekly")
    MONTHLY = ("monthly", "Monthly")
    FORTNIGHTLY = ("fortnightly", "Fortnightly")


@model_prefix("jobsch")
class JobSchedule(SoftDeleteModel):
    job = models.ForeignKey(
        Job, null=False, blank=False, on_delete=models.CASCADE, related_name="schedules"
    )

    frequency = models.CharField(
        null=False, max_length=20, choices=Frequency.as_tuples()
    )

    week_of_month = ArrayField(
        models.IntegerField(null=True, blank=True),
        null=True,
        blank=True,
    )
    day_of_week = ArrayField(
        models.CharField(null=True, max_length=20, choices=DaysOfWeek.as_tuples()),
        null=True,
        blank=True,
    )

    date_of_month = ArrayField(
        models.IntegerField(
            null=True, validators=[MaxValueValidator(31), MinValueValidator(1)]
        ),
        null=True,
        blank=True,
    )

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):

        if self.frequency == Frequency.WEEKLY.ident and not self.day_of_week:
            raise ValidationError(
                "When the frequency is weekly, specifying day of week is mandatory"
            )

        if self.frequency == Frequency.MONTHLY.ident and not self.date_of_month:
            raise ValidationError(
                "When the frequency is monthly, specifying date of month is mandatory"
            )

        if self.date_of_month:
            if any([(x < 1 or x > 31) for x in self.date_of_month]):
                raise ValidationError("Date of a month must be between 1 and 31")

        return super().save(force_insert, force_update, using, update_fields)

    def match(self, timestamp: datetime.datetime) -> bool:
        """Does this timestamp fall under this schedule?"""
        week_of_month = (timestamp.day - 1) // 7 + 1
        day_of_week = timestamp.weekday()
        day_of_week = calendar.day_name[day_of_week].lower()
        date_of_month = timestamp.day

        if self.frequency is None or self.frequency == Frequency.DAILY.ident:
            return True

        if self.frequency == Frequency.WEEKLY.ident:
            if day_of_week in self.day_of_week:
                if self.week_of_month and week_of_month not in self.week_of_month:
                    return False

                return True

        elif self.frequency == Frequency.MONTHLY.ident:
            if self.day_of_week and day_of_week in self.day_of_week:
                return True

            if self.date_of_month and date_of_month in self.date_of_month:
                return True

        return False

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["job"],
                condition=(~Q(is_deleted=True)),
                name="jobconfig_jobschedule_job_unique_exclude_deleted",
            )
        ]


@model_prefix("jobrule")
class JobAlertRule(SoftDeleteModel):
    job = models.ForeignKey(
        Job,
        null=False,
        blank=False,
        on_delete=models.CASCADE,
        related_name="alert_rules",
    )
    # Way to read this is - This job receives 5 (expected_document_count) invoices in 3 (period) weeks (period_type)
    expected_document_count = models.IntegerField()
    period = models.CharField(null=False, max_length=20, choices=Period.as_tuples())
    period_count = models.IntegerField()
    enabled = models.BooleanField()


class JobStat(models.Model):
    id = PrefixedIdField(primary_key=True, prefix="jobstats")
    job = models.ForeignKey(
        Job, null=False, blank=False, on_delete=models.CASCADE, related_name="stats"
    )

    # all dates are as per PST timezone
    date = models.DateField(Job, null=False, blank=False)

    is_customer_scheduled = models.BooleanField(null=True, blank=False, default=None)

    run_total_count = models.IntegerField(null=True, blank=False, default=None)
    run_success_count = models.IntegerField(null=True, blank=False, default=None)
    run_manual_all_count = models.IntegerField(null=True, blank=False, default=None)
    run_login_failure_count = models.IntegerField(null=True, blank=False, default=None)

    df_count = models.IntegerField(null=True, blank=True)

    def _do_insert(self, manager, using, fields, returning_fields, raw):
        if not returning_fields:
            returning_fields = []

        if "id" not in returning_fields:
            returning_fields.append(self._meta.auto_field)

        if not raw:
            fields = [f for f in fields if f.attname != "id"]

        results = super()._do_insert(manager, using, fields, returning_fields, raw)

        self.id = results[-1]  # pylint: disable=attribute-defined-outside-init
        results = results[:-1]
        return results

    class Meta:
        indexes = [
            models.Index(fields=["job"]),
            models.Index(fields=["date"]),
            models.Index(fields=["job", "date"]),
        ]
