from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from spices.django3 import storage_utils
from spices.django3.base_model.models import model_prefix, BaseModel, AbstractBaseModel
from spices.django3.coreobjects.base import SharedCoreObjectModel
from spices.django3.fields import CharChoiceField
from spices.enum_utils import BaseChoice


class Channel(BaseChoice):
    """To differentiate among various type of connectors eg. vendor, accounting etc."""

    WEB = ("WEB", "Web")
    FTP = ("FTP", "FTP")


class ConnectorType(BaseChoice):
    """To differentiate among various type of connectors eg. vendor, accounting etc."""

    VENDOR = ("VENDOR", "Vendor")
    ACCOUNTING = ("ACCOUNTING", "Accounting")


class EntityType(BaseChoice):
    """Entity types that can be discovered / pulled / downloaded from integrated connectors"""

    # alphabetical
    BANK_ACCOUNT = ("bank_account", "Bank Account")
    GL_ACCOUNT = ("gl_account", "GL Account")
    INVOICE = ("invoice", "Invoice")
    PAYMENT = ("payment", "Payment Information")
    STATEMENT = ("statement", "Statement")
    VENDOR = ("vendor", "Vendor")
    ORDER_GUIDE = ("order_guide", "Order Guide")
    PURCHASE_ORDER = ("purchase_order", "Purchase Order")


class SupportedFileType(BaseChoice):
    """Supported File Types eg. pdf, csv, xls etc."""

    PDF = ("pdf", "pdf")
    CSV = ("csv", "csv")
    XLS = ("xls", "xls")
    JSON = ("json", "json")
    XML = ("xml", "xml")


class SupportedCustomProperties(BaseChoice):
    """Supported Customer Properties at Connector & Job Level"""

    STRICT_LOCATION_CHECK = ("strict_location_check", "Strict Location Check (R365)")
    STRICT_BANK_ACC_CHECK = (
        "strict_bank_acc_check",
        "Strict Bank Account Check (R365)",
    )
    R365_AUTO_APPROVE = ("r365_auto_approve", "Auto Approve (R365)")
    VPN_REQUIRED = ("vpn_required", "VPN Required")
    COMPUTE_EXTRACTED_TEXT_HASH = (
        "compute_extracted_text_hash",
        "Compute Extracted Text Hash",
    )
    DOWNLOAD_FUTURE_INVOICES = ("download_future_invoices", "Download Future Invoices")
    CELERY_TASK_TIME_LIMIT = ("celery_task_time_limit", "Celery Task Time limit")


# noinspection PyUnusedLocal
def generate_image_name(obj, file_name):  # pylint: disable=unused-argument
    obj_id = obj.id.replace("~", "").replace(".", "")
    date_string = timezone.now().strftime("%Y%m%d-%H%M%S")
    return f"{obj_id}-{date_string}"


class ConnectorDisabledReason(BaseChoice):
    NOT_IMPLEMENTED = ("not-implemented", "Not yet integrated")
    INVOICES_NOT_PROVIDED = (
        "invoices-not-provided",
        "This connection doesn't provide invoices",
    )
    BLOCKED__REQUIRES_2FA = ("requires2fa", "Requires 2FA")
    BLOCKED__CAPTCHA = ("captcha", "Requires Captcha Resolution")
    OTHER = ("other", "Other")


class ConnectorCapabilityTypes(BaseChoice):
    # will need this to support a simple "login" action
    INTERNAL__WEB_LOGIN = ("internal.web_login", "Login to the website")
    BANK_ACCOUNT__IMPORT_LIST = ("bank.import_list", "Import Bank Accounts")
    GL__IMPORT_LIST = ("gl.import_list", "Import GL Accounts")
    INVOICE__DOWNLOAD = ("invoice.download", "Download Invoices")
    INVOICE__EXPORT = ("invoice.export", "Export Verified Invoices")
    ORDER_GUIDE__DOWNLOAD = ("order_guide.download", "Download Order Guides")
    PAYMENT__PAY = ("payment.pay", "Make payments")
    PAYMENT__IMPORT_INFO = ("payment.import", "Import Payment Information")
    PAYMENT__EXPORT_INFO = ("payment.export", "Export Payment Information")
    PO_DOWNLOAD = ("po.download", "Download Purchase Orders")
    STATEMENT__DOWNLOAD = ("statement.download", "Download Statements")
    VENDOR__IMPORT_LIST = ("vendor.import_list", "Import Vendor List")
    ACCOUNTING__IMPORT_MULTIPLE_ENTITIES = (
        "accounting.import_multiple_entities",
        "Import Multiple Entities",
    )


@model_prefix("conn")
class Connector(BaseModel):
    """
    This is one (specific) website for a particular vendor/group/Account.
    For example,
        - Regal Wine Co is a vendor/group registered with Bill Trust (billtrust.com)
        - Their specific part of the website is: secure.billtrust.com/regalbilltrust/
        - In this example, Bill Trust is the Adapter, and (BillTrust + Regal) is the VendorSite

    In case of individual vendor/group/accounting websites, the URL will be the same as the Adapter URL.
    Even in this case, a Site record is still needed but the URL can be optionally left NULL.

    ** This is what is actually used for figuring out which type of site to crawl.

    :ivar text name: Name of the Connector
    :ivar str login_url: Website Login URL for the VendorSite.
    :ivar str registration_url: Website Registration URL for the Connector.
    :ivar bool enabled: Whether this Connector is ready for use
    :ivar str type: Determines the type of Connector. eg. vendor connector or accounting connector
    :ivar str adapter_code: The unique string representing the connector.
    :ivar str channel: Defines the channel from where the documents are expected eg. Web/FTP etc.
                       This controls what credentials to expect / look for when executing a run.
    """

    adapter_code = models.CharField(
        max_length=50, null=True, blank=False, db_index=True
    )
    channel = CharChoiceField(
        choices=Channel, null=False, max_length=50, default=Channel.WEB
    )
    type = models.CharField(
        null=False, choices=ConnectorType.as_tuples(), max_length=50, default=None
    )

    name = models.TextField(null=False, blank=False)
    enabled = models.BooleanField(null=False, default=None)
    disabled_reason = CharChoiceField(
        choices=ConnectorDisabledReason, blank=True, null=True, max_length=64
    )
    disabled_reason_text = models.TextField(null=True, blank=True)

    login_url = models.TextField(null=True, blank=True)
    registration_url = models.TextField(null=True, blank=True, default=None)
    # If you are testing this in LOCAL_ENV, and you're able to save the icon but not see it,
    # that is because policies on `com.qubiqle.integrator.dev` prevent public objects. This is not a bug.
    # (this will work correctly in prod by default, since the bucket policies allow public objects).
    # If you want to be able to see the icon in local, just go to the bucket and mark relevant objects
    # as public. DO NOT mark the bucket as public.
    icon = models.FileField(
        storage=storage_utils.get_s3_storage(
            settings.INTEGRATOR_ICON_BUCKET,
            location="assets/images/logos/integrator/",
            querystring_auth=False,
            default_acl="public-read",
        ),
        max_length=512,
        upload_to=generate_image_name,
        null=True,
        blank=True,
    )

    hidden = models.BooleanField(null=False, default=False)

    # Following rank is for priority of the connector crawler will be picked up.
    backlog_rank = models.IntegerField(null=True, blank=True)
    # following date is for what time a connector crawler will be available for the users.
    etd_date = models.DateTimeField(default=None, null=True, blank=True)
    # Following frequency is for crawlers/runs of the connector crawler will be picked up.
    frequency = models.IntegerField(null=True, blank=True)
    custom_properties = JSONField(null=True, blank=True)
    # invoice url from where you can download the invoices
    invoice_download_url = models.TextField(null=True, blank=True)
    # video url of how to get the invoices from particular website(connector)
    video_url = models.TextField(null=True, blank=True)

    @property
    def effective_url(self) -> str:
        """Effective URL for Connector"""
        return str(self.login_url) if self.login_url else None

    @property
    def has_configurable_login_url(self) -> bool:
        """for r365_v1 we're saving login url in job."""
        return self.adapter_code == "r365_v1"

    def has_capability(self, capability: ConnectorCapabilityTypes) -> bool:
        """validating whether connector has a capability or not"""
        if isinstance(capability, str):
            capability = ConnectorCapabilityTypes(capability)

        if capability is ConnectorCapabilityTypes.ACCOUNTING__IMPORT_MULTIPLE_ENTITIES:
            return self.capabilities.filter(
                type__in=[
                    ConnectorCapabilityTypes.BANK_ACCOUNT__IMPORT_LIST,
                    ConnectorCapabilityTypes.GL__IMPORT_LIST,
                    ConnectorCapabilityTypes.VENDOR__IMPORT_LIST,
                    ConnectorCapabilityTypes.ACCOUNTING__IMPORT_MULTIPLE_ENTITIES,
                ]
            ).exists()

        return self.capabilities.filter(type=capability).exists()

    @property
    def is_backlog(self) -> bool:
        """Is this adapter a backlog adapter?"""
        return self.adapter_code == "backlog"

    @property
    def is_manual(self) -> bool:
        """Is this adapter a manual adapter?"""
        return self.adapter_code == "manual"

    @property
    def get_supported_invoice_format(self) -> str:
        """file format supported by connector"""
        try:
            capability = self.capabilities.get(
                type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
            )
        except ConnectorCapability.DoesNotExist:
            capability = None
        return capability.supported_file_format if capability else "pdf"

    @property
    def get_custom_properties(self) -> dict:
        """custom properties for connector"""
        return self.custom_properties if self.custom_properties else {}

    def __str__(self):
        return f"{self.name}"


class ConnectorVendorInfo(AbstractBaseModel):
    """
    One individual Vendor/Group's AR website. This is one (specific) website for a particular vendor/group.
    Of course, at least one of Vendor and Vendor Group is required (technically Vendor Group is always required,
    but the PIQ system can have Vendors without Groups, so it's left nullable.

    For example,
        - Regal Wine Co is a vendor/group registered with Bill Trust (billtrust.com)
        - Their specific part of the website is: secure.billtrust.com/regalbilltrust/
        - In this example, Bill Trust is the Adapter, and (BillTrust + Regal) is the VendorSite

    In case of individual vendor/group websites, the URL will be the same as the Adapter URL. Even in
    this case, a Vendor Site record is still needed but the URL can be optionally left NULL.

    ** This is what is actually used for figuring out which vendor/group to crawl.

    :ivar Connector connector: connector
    :ivar VendorGroup vendor_group_id: Vendor Group to whom this particular VendorSite belongs
    :ivar Vendor vendor_id: Vendor to whom this particular VendorSite belongs
    :ivar bool contains_support_document: Default=False & True means there are supporting documents apart from invoice
    """

    connector = models.OneToOneField(
        Connector,
        related_name="connector_vendor",
        primary_key=True,
        on_delete=models.PROTECT,
    )
    vendor = models.ForeignKey(
        SharedCoreObjectModel,
        related_name="vendor_cvis",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    vendor_group = models.ForeignKey(
        SharedCoreObjectModel,
        related_name="vendor_group_cvis",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )
    contains_support_document = models.BooleanField(null=False, default=None)
    requires_account_number = models.BooleanField(null=False, default=False)

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        if not self.vendor_id and not self.vendor_group_id:
            raise ValidationError("Need at least one of VendorGroup or Vendor")

        return super().save(force_insert, force_update, using, update_fields)

    def __str__(self):
        return f"ConnectorVendorInfo: {self.connector}"


@model_prefix("concp")
class ConnectorCapability(BaseModel):
    """
    A connector can have multiple capabilities, this table is for storing those capabilities
    For example,
        - A BillTrust connector have capability import.invoices
        - A Baldor connector have capability export.payments
        - In this example, Bill Trust, Baldor is the Connector,
        and (import.invoices + export.payments) is the Capability
    ** This is what is actually used for figuring out what things are supported by a connector while crawl.
    :ivar Connector connector: connector
    :ivar str type: Defines the types of capabilities a connector supports eg. export.payments/import.invoices etc.
                   This controls what things should be run while executing engine.crawl.
    """

    type = CharChoiceField(choices=ConnectorCapabilityTypes, max_length=256)
    supported_file_format = CharChoiceField(
        choices=SupportedFileType, max_length=64, null=True, blank=True
    )
    connector = models.ForeignKey(
        Connector, null=False, related_name="capabilities", on_delete=models.PROTECT
    )

    class Meta:
        unique_together = [
            ("connector", "type"),
        ]

    def __str__(self):
        return f"For Connector: {self.connector} ConnectorCapabilityType: {self.type}"
