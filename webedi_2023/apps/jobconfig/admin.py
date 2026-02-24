from typing import Dict, Union

from dal import autocomplete, forward
from django import forms
from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.admin.utils import unquote
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import QuerySet
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django_better_admin_arrayfield.admin.mixins import DynamicArrayMixin
from spices.django3 import thread_local
from spices.django3.admin.utils import to_link, action_short_description, BaseAdmin
from spices.django3.coreobjects.models import Location, Account, LocationGroup, Company

from apps.definitions.admin import BacklogFilter
from apps.definitions.models import (
    Channel,
    ConnectorCapabilityTypes,
    ConnectorCapability,
)
from apps.jobconfig import LOGGER
from apps.jobconfig.models import Job, PIQMapping, FileDiscoveryAction, ConnectorRequest
from apps.runs.models import RunCreatedVia
from apps.runs.run_factory import create_run
from integrator import settings


def _trigger_new_execution(
    modeladmin, request, queryset: QuerySet, operation: ConnectorCapabilityTypes
):
    """Create runs for jobs in queryset and execute them asynchronously"""
    jobs = list(queryset.all())
    LOGGER.info(
        f"[tag:WJCATNC10] User {request.user.remote_id} requested an on-demand run"
        f" (with operation {operation})"
        f" for selected jobs: {[j.id for j in jobs]}"
    )

    created = {}
    ignored = []

    for job in jobs:  # type: Job
        if not job.connector.has_capability(operation):
            ignored.append(job)
            continue

        LOGGER.info(f"[tag:WJCATNC20] Run requested for job id {job.id}")
        run = create_run(job, operation, RunCreatedVia.ADMIN_REQUEST)
        if run:
            run.execute_async(on_demand=True)
            created[run.id] = job
        else:
            ignored.append(job)

    created = ", ".join(
        [
            f'<a href="{reverse("admin:runs_run_change", args=(rid,))}">{str(j)}</a>'
            for rid, j in created.items()
        ]
    )
    message = f"Successfully triggered jobs: {created or None}"
    level = messages.INFO
    if ignored:
        level = messages.WARNING
        message = (
            message
            + f' (ignored {len(ignored)} jobs: {", ".join([str(j) for j in jobs])})'
        )

    modeladmin.message_user(request, message=mark_safe(message), level=level)

    # if the user was on a page with filters set, we want to send the user back to the same page
    redirect_to = request.META.get("HTTP_REFERER") or reverse(
        "admin:jobconfig_job_changelist"
    )
    return HttpResponseRedirect(redirect_to)


def delete_job(modeladmin: admin.ModelAdmin, request, queryset: QuerySet):
    """Delete jobs in queryset"""
    jobs = list(queryset.all())
    LOGGER.info(
        f"[tag:WJCATDJ10] User {request.user.remote_id} requested an on-demand delete"
        f" for selected jobs: {[j.id for j in jobs]}"
    )
    deleted_job = []
    for job in jobs:  # type: Job
        LOGGER.info(f"[tag:WJCATDJ20] Delete requested for job id {job.id}")
        job.delete()
        deleted_job.append(job.id)
    message = f'Successfully deleted jobs : {",".join(str(job) for job in deleted_job)}'
    level = messages.INFO

    modeladmin.message_user(request, message=mark_safe(message), level=level)

    # if the user was on a page with filters set, we want to send the user back to the same page
    redirect_to = reverse("admin:jobconfig_job_changelist")
    return HttpResponseRedirect(redirect_to)


class FileDiscoveryActionInline(admin.TabularInline):
    model = FileDiscoveryAction
    extra = 0
    fields = ["job", "document_type", "action_type", "edi_parser_code"]
    ordering = ("document_type",)


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ["location", "location_group", "companies"]
        widgets = {
            "account": autocomplete.ModelSelect2(
                url="coreobjects-autocomplete",
                forward=[
                    (forward.Const(Account.__coreobjects_type__, "type")),
                ],
            ),
            "location_group": autocomplete.ModelSelect2(
                url="coreobjects-autocomplete",
                forward=[
                    (forward.Const(LocationGroup.__coreobjects_type__, "type")),
                ],
            ),
            "location": autocomplete.ModelSelect2(
                url="coreobjects-autocomplete",
                forward=[
                    (forward.Const(Location.__coreobjects_type__, "type")),
                ],
            ),
            "companies": autocomplete.ModelSelect2Multiple(
                url="coreobjects-autocomplete",
                forward=[
                    (forward.Const(Company.__coreobjects_type__, "type")),
                ],
            ),
        }

    _request: WSGIRequest

    def clean(self):
        request = thread_local.get_current_request()
        setattr(self, "_request", request)

        super().clean()
        self._warn_if_ftp_job_enabled_without_credentials()
        return self.cleaned_data

    def clean_login_url(self):
        if "connector" in self.cleaned_data:
            try:
                connector = self.instance.connector
            except ObjectDoesNotExist:
                connector = self.cleaned_data["connector"]
            if (
                connector.adapter_code == "r365_v1"
                and not self.cleaned_data["login_url"]
            ):
                raise ValidationError("Login url is mandatory for r365 jobs.")
            return self.cleaned_data.get("login_url", "")
        return self.cleaned_data.get("login_url", "")

    def _warn_if_ftp_job_enabled_without_credentials(self):
        if "connector" in self.cleaned_data:
            try:
                connector = self.instance.connector
            except ObjectDoesNotExist:
                connector = self.cleaned_data["connector"]

            if (
                self.cleaned_data["enabled"]
                and not self.cleaned_data.get("ftp_credential")
                and connector.channel == Channel.FTP
            ):
                msg = "You enabled an FTP EDI Job without FTP Credential. Are you sure?! The cronjob will not run."
                messages.warning(self._request, msg)


def _update_jobs_for_manual_process(
    modeladmin, request, enable_for_manual: bool, jobs: list
):
    LOGGER.info(
        f"[tag:WJCATNC10] User {request.user.remote_id} requested for updating jobs for manual process"
        f" enable_for_manual: {enable_for_manual}"
        f" for selected jobs: {[j.id for j in jobs]}"
    )

    created = {}
    ignored = []

    for job in jobs:  # type: Job
        job.enabled_for_manual = enable_for_manual
        job.save()

        LOGGER.info(f"[tag:WJCATNC20] Run requested for job id {job.id}")
        try:
            run = create_run(
                job,
                ConnectorCapabilityTypes.INVOICE__DOWNLOAD,
                RunCreatedVia.ADMIN_REQUEST,
            )
        except Exception as exc:  # pylint: disable=broad-except
            run = None
            LOGGER.info(
                f"[tag:WJCATNC30] Run creation failed for job id {job.id} with exc : {exc}"
            )
        if run:
            run.is_manual = True
            run.save()
            run.execute_async(on_demand=True)
            created[run.id] = job
        else:
            ignored.append(job)

    created = ", ".join(
        [
            f'<a href="{reverse("admin:runs_run_change", args=(rid,))}">{str(j)}</a>'
            for rid, j in created.items()
        ]
    )
    message = f"Successfully Updated jobs for manual process: {created or None}"
    level = messages.INFO
    if ignored:
        level = messages.WARNING
        message = (
            message
            + f' (ignored {len(ignored)} jobs: {", ".join([str(j) for j in jobs])})'
        )

    modeladmin.message_user(request, message=mark_safe(message), level=level)

    # if the user was on a page with filters set, we want to send the user back to the same page
    redirect_to = request.META.get("HTTP_REFERER") or reverse(
        "admin:jobconfig_job_changelist"
    )
    return HttpResponseRedirect(redirect_to)


@admin.register(Job)
class JobAdmin(BaseAdmin, DynamicArrayMixin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            url(
                r"^(?P<job_id>.+)/trigger-operation/(?P<operation>.+)/$",
                self.admin_site.admin_view(self.trigger_operation),
                name="trigger-operation",
            ),
            url(
                r"^(?P<job_id>.+)/delete/$",
                self.admin_site.admin_view(self.delete_job_confirmation),
                name="delete-job-action",
            ),
            url(
                r"^(?P<job_id>.+)/enabled-for-manual/$",
                self.admin_site.admin_view(self.enable_manual_invoice_download),
                name="enable-manual-invoice-download",
            ),
        ]
        return custom_urls + urls

    def has_delete_permission(self, request, obj=None):
        # added this method, so there wont be default delete button inside the details page.
        return False

    # pylint: disable=no-self-use
    @action_short_description("Show login url")
    def login_url_shortcut(self, obj: Job):
        login_url = obj.connector.login_url or obj.login_url
        login_url_html = f'<a href="{login_url}">{login_url}</a>'
        return format_html(login_url_html)

    connector_link = to_link("connector", short_description="Connector")

    fieldsets = [
        (
            "Quick Links",
            {
                "fields": (
                    "connector_link",
                    "shortcuts",
                    "login_url_shortcut",
                    "customer_number_mappings",
                ),
            },
        ),
        (
            "Basic",
            {
                "fields": (
                    "id",
                    "connector",
                    "username",
                    "password",
                    "account",
                    "location_group",
                    "location",
                    "companies",
                    "enabled",
                    "disabled_reason",
                    "disabled_reason_text",
                    "notes",
                    "login_url",
                    "encryption_manager",
                    "ftp_credential",
                    "custom_properties",
                ),
            },
        ),
        (
            "Creation / Updation info",
            {
                "fields": (
                    "last_modified_date",
                    "last_modified_user",
                    "created_date",
                    "created_user",
                    "disabled_at_date",
                    "disabled_by_user",
                ),
            },
        ),
    ]

    search_fields = (
        "id",
        "username",
        "connector__name",
        "connector__adapter_code",
        "account__display_name",
        "location_group__display_name",
        "location__display_name",
    )
    list_display = (
        "id",
        to_link("connector", short_description="Connector"),
        "username",
        "account_name",
        "location_group_name",
        "location_name",
        "enabled",
        "trigger_actions",
        "delete_action",
    )
    list_filter = (
        "enabled",
        "connector__type",
        "enabled_for_manual",
        BacklogFilter.new(join_prefix="connector__"),
        "connector__adapter_code",
    )
    ordering = ("-created_date",)

    form = JobForm

    inlines = [FileDiscoveryActionInline]

    def get_queryset(self, request):
        queryset = (
            super()
            .get_queryset(request)
            .select_related("connector", "account", "location", "location_group")
            .prefetch_related("connector__capabilities")
        )
        return queryset

    @classmethod
    def account_name(cls, obj):
        return (
            f"{obj.account.remote_id} - {obj.account.display_name}"
            if obj.account
            else None
        )

    @classmethod
    def location_name(cls, obj):
        return (
            f"{obj.location.remote_id} - {obj.location.display_name}"
            if obj.location
            else None
        )

    @classmethod
    def location_group_name(cls, obj):
        return (
            f"{obj.location_group.remote_id} - {obj.location_group.display_name}"
            if obj.location_group
            else None
        )

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    # pylint: disable=unused-argument,no-self-use
    def encryption_manager(self, obj):
        return settings.ENCRYPTED_FIELD_KEY_MANAGER.name

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # This is add to remove edit/delete options for foreign keys
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)

        if db_field.name in (
            "connector",
            "account",
            "location_group",
            "location",
            "vendor_group",
        ):
            formfield.widget.can_delete_related = False
            formfield.widget.can_change_related = False

        return formfield

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        readonly_fields += [
            "shortcuts",
            "connector_link",
            "encryption_manager",
            "login_url_shortcut",
            "disabled_at_date",
            "disabled_by_user",
            "customer_number_mappings",
        ]
        if obj:  # editing an existing object
            return readonly_fields + ["connector", "trigger_actions", "account"]
        return readonly_fields

    def get_autocomplete_fields(self, request):
        return ["connector", "ftp_credential", "account", "location", "location_group"]

    @staticmethod
    def shortcuts(obj):
        if not obj or not obj.id:
            return "-"

        runs_url = f"{reverse('admin:runs_run_changelist')}?job={obj.id}"
        discoveredfile_url = (
            f"{reverse('admin:runs_discoveredfile_changelist')}?filter_job_id={obj.id}"
        )
        checkruns_url = f"{reverse('admin:runs_checkrun_changelist')}?run__job={obj.id}"
        other_jobs_url = (
            f"{reverse('admin:jobconfig_job_changelist')}?connector={obj.connector_id}"
        )

        return format_html(
            f"""
                <div>
                    <span><a href="{runs_url}">Related Runs</a></span>
                    &nbsp;&nbsp;|&nbsp;&nbsp;
                    <span><a href="{discoveredfile_url}">Related Discovered Files </a></span>
                    &nbsp;&nbsp;|&nbsp;&nbsp;
                    <span><a href="{checkruns_url}">Related CheckRuns</a></span>
                    &nbsp;&nbsp;|&nbsp;&nbsp;
                    <span><a href="{other_jobs_url}">Other jobs for the same connector</a></span>
                </div>
            """
        )

    @action_short_description("Customer Number Mappings")
    def customer_number_mappings(self, obj: Job):
        _url = f"{settings.PIQ_API_BASE_URL}/admin/integrations/edimapping/?q-l=on&q=ref_job_id+%3D+%22{obj.id}%22"
        return format_html(
            f'<a href="{_url}">Go to customer number mappings for this job</a>'
        )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        # Unquoting added values from django to object_id to get exact object_id.
        # https://github.com/django/django/blob/master/django/contrib/admin/utils.py#L63
        job = self.get_object(request, unquote(object_id))
        if not job:
            return self._get_obj_does_not_exist_redirect(
                request, self.model._meta, object_id
            )

        LogEntry.objects.log_action(
            user_id=request.user.id,
            content_type_id=ContentType.objects.get_for_model(job).pk,
            object_id=job.id,
            object_repr=str(job),
            action_flag=CHANGE,
            change_message="opened",
        )

        return super(JobAdmin, self).change_view(
            request, object_id, form_url, extra_context
        )

    def save_model(self, request, obj, form, change):
        if "enabled" in form.changed_data or ("disabled_reason" in form.changed_data):
            if (
                "disabled_reason" in form.changed_data
                or "disabled_reason_text" in form.changed_data
                or not obj.enabled
            ):
                if obj.disabled_reason or obj.disabled_reason_text:
                    obj.enabled = False
                    obj.disabled_by_user = request.user
                    obj.disabled_at_date = timezone.now()
            elif obj.enabled:
                obj.disabled_by_user = None
                obj.disabled_reason = None
                obj.disabled_reason_text = None
                obj.disabled_at_date = None
        super().save_model(request, obj, form, change)

    # ############################## Actions Section ####################################
    @action_short_description("Trigger Operation")
    def trigger_operation(self, request, job_id: str, operation: str):
        """
        Main Controller which handles any trigger run requests for given job(s) + operation

        :param request: Request
        :param job_id: This can be queryset (if called from django admin list action) or str if called
                       from django `admin/jobconfig/job/<job_id>/crawl/` view
        :param operation: What operation to perform for job
        :return:
        """
        queryset = Job.objects.filter(pk=job_id)
        return _trigger_new_execution(
            self, request, queryset, ConnectorCapabilityTypes(operation)
        )

    @action_short_description("Download Invoices")
    def _trigger_run__download_invoices(self, request, queryset):
        """Create ane execute run for downloading invoices"""
        return _trigger_new_execution(
            self, request, queryset, ConnectorCapabilityTypes.INVOICE__DOWNLOAD
        )

    @action_short_description("Export Payments")
    def _trigger_run__export_payments(self, request, queryset):
        """Create ane execute run for exporting payments"""
        return _trigger_new_execution(
            self, request, queryset, ConnectorCapabilityTypes.PAYMENT__EXPORT_INFO
        )

    @action_short_description("Import Accounting Entities")
    def _trigger_run__import_accounting_entities(self, request, queryset):
        """Create ane execute run for importing accounting entities"""
        return _trigger_new_execution(
            self,
            request,
            queryset,
            ConnectorCapabilityTypes.ACCOUNTING__IMPORT_MULTIPLE_ENTITIES,
        )

    @action_short_description("Actions")
    def trigger_actions(self, obj: Job):
        if not obj.is_active():
            return "Disabled"

        if obj.connector.is_backlog:
            return "Fake"

        if obj.connector.is_manual:
            return "Manual DE only"

        buttons = []

        # we do this to use prefetch and prevent DB queries
        obj_capabilities = [cap.type for cap in obj.connector.capabilities.all()]

        # buttons for invoice download, payment export, payment import
        capabilities = [
            ConnectorCapabilityTypes.INVOICE__DOWNLOAD,
            ConnectorCapabilityTypes.PAYMENT__IMPORT_INFO,
            ConnectorCapabilityTypes.PAYMENT__EXPORT_INFO,
        ]
        for capability in capabilities:
            if capability in obj_capabilities:
                _text = capability.message  # pylint: disable=no-member
                _url = reverse(
                    "admin:trigger-operation",
                    args=[obj.pk, capability.ident],  # pylint: disable=no-member
                )
                crawl_button = f'<a class="button" href="{_url}">{_text}</a>'
                buttons.append(crawl_button)

        # button for accounting import (sync)
        accounting_import_capabilities = [
            ConnectorCapabilityTypes.BANK_ACCOUNT__IMPORT_LIST,
            ConnectorCapabilityTypes.GL__IMPORT_LIST,
            ConnectorCapabilityTypes.VENDOR__IMPORT_LIST,
        ]
        if any(cap in obj_capabilities for cap in accounting_import_capabilities):
            _url = reverse(
                "admin:trigger-operation",
                args=[
                    obj.pk,
                    ConnectorCapabilityTypes.ACCOUNTING__IMPORT_MULTIPLE_ENTITIES,
                ],
            )
            crawl_button = f'<a class="button" href="{_url}">Import Accounting Info</a>'
            buttons.append(crawl_button)

        return format_html("<br/><br/>".join(buttons))

    trigger_actions.allow_tags = True

    @action_short_description("Delete job")
    def delete_job_confirmation(self, request, job_id):
        """
        :param request: Request
        :param job_id: This can be queryset (if called from django admin list action) or str if called
                       from django `admin/jobconfig/job/<job_id>/delete/` view
        :return:
        """
        queryset = Job.objects.filter(pk=job_id) if isinstance(job_id, str) else job_id
        if request.POST.get("post"):
            if request.POST.get("is_bulk_delete"):
                queryset = Job.objects.filter(
                    pk__in=request.POST.getlist("bulk_object_ids")
                )
            return delete_job(self, request, queryset)

        object_id = job_id
        is_bulk_delete = False
        if not isinstance(job_id, str):
            object_id = queryset[0].id
            is_bulk_delete = True
        context = {
            "title": "Delete job",
            "deleted_objects": queryset,
            "action_checkbox_name": "delete-job",
            "is_bulk_delete": is_bulk_delete,
            "opts": Job._meta,
            "object_id": object_id,
            "site_header": settings.DJANGO_ADMIN_SITE_HEADER,
        }
        return TemplateResponse(
            request, "jobconfig/delete_job_confirmation.html", context
        )

    delete_job_confirmation.allow_tags = True

    @staticmethod
    def delete_action(obj):
        delete_url = reverse("admin:delete-job-action", args=[obj.pk])
        delete_button = (
            f'<br/><br/><a class="button" style="background:#ba2121;color:white;" '
            f'href="{delete_url}">Delete</a>'
        )
        return format_html(delete_button)

    @action_short_description("Enable manual invoice download")
    def enable_manual_invoice_download(self, request, job_id):
        """
        :param request: Request
        :param job_id: This can be queryset (if called from django admin list action) or str if called
                       from django `admin/jobconfig/job/<job_id>/enabled-for-manual/` view
        :return:
        """

        jobs = Job.objects.filter(pk=job_id) if isinstance(job_id, str) else job_id
        return _update_jobs_for_manual_process(self, request, True, jobs)

    @action_short_description("Disable manual invoice download")
    def disable_manual_invoice_download(self, request, job_id):
        """
        :param request: Request
        :param job_id: This can be queryset (if called from django admin list action) or str if called
                       from django `admin/jobconfig/job/<job_id>/enabled-for-manual/` view
        :return:
        """

        jobs = Job.objects.filter(pk=job_id) if isinstance(job_id, str) else job_id
        return _update_jobs_for_manual_process(self, request, False, jobs)

    actions = [
        _trigger_run__download_invoices,
        _trigger_run__export_payments,
        _trigger_run__import_accounting_entities,
        delete_job_confirmation,
        enable_manual_invoice_download,
        disable_manual_invoice_download,
    ]


@admin.register(PIQMapping)
class PIQMappingAdmin(BaseAdmin):
    fields = [f.name for f in PIQMapping._meta.concrete_fields]
    search_fields = (
        "job__connector__name",
        "piq_data__remote_id",
        "piq_data__display_name",
        "mapping_data",
    )
    list_display = (
        "id",
        to_link("job", short_description="Job"),
        "type",
        to_link("piq_data", short_description="PIQ Data"),
        "mapping_data",
        "mapped_to",
    )
    list_filter = (
        "piq_data__type",
        "job__connector",
    )
    list_select_related = ["job", "job__connector", "piq_data", "job__account"]
    ordering = ("-created_date",)

    @classmethod
    def type(cls, obj):
        return f"{obj.piq_data.type}" if obj.piq_data else None

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:  # editing an existing object
            return readonly_fields + ["job"]
        return readonly_fields

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # This is add to remove edit/delete options for foreign keys
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)

        if db_field.name == "piq_data":
            formfield.widget.can_delete_related = False
            formfield.widget.can_change_related = False

        return formfield


def convert_connector_request_to_job(
    modeladmin: admin.ModelAdmin,
    request,
    queryset: QuerySet,
    create_job_kwargs: Dict = None,
):
    """Create jobs for connector requests in queryset and execute them asynchronously"""
    connector_requests = list(queryset.all())
    LOGGER.info(
        f"[tag:CCRTJ10] User {request.user.remote_id} requested an on-demand run"
        f" (with params {create_job_kwargs})"
        f" for selected connector_requests: {[cr.id for cr in connector_requests]}"
    )

    created = {}
    ignored = []

    for connector_request in connector_requests:
        LOGGER.info(
            f"[tag:CCRTJ20] job requested for connector_request id {connector_request.id}"
        )
        connector = connector_request.converted_to_connector
        if connector and not connector_request.converted_to_job:
            if not connector.has_capability(ConnectorCapabilityTypes.INVOICE__DOWNLOAD):
                cc = ConnectorCapability(
                    connector=connector, type=ConnectorCapabilityTypes.INVOICE__DOWNLOAD
                )
                cc.save()
            created[connector_request.convert_to_job().id] = connector_request
        else:
            ignored.append(connector_request)

    created = ", ".join(
        [
            f'<a href="{reverse("admin:jobconfig_connectorrequest_change", args=(jid,))}">{str(cr)}</a>'
            for jid, cr in created.items()
        ]
    )
    message = f"Successfully converted connector requests to jobs : {created or None}"
    level = messages.INFO
    if ignored:
        level = messages.WARNING
        message = (
            message
            + f' (ignored {len(ignored)} connector_requests: {", ".join([j.name for j in connector_requests])})'
        )

    modeladmin.message_user(request, message=mark_safe(message), level=level)

    # if the user was on a page with filters set, we want to send the user back to the same page
    redirect_to = request.META.get("HTTP_REFERER") or reverse(
        "admin:jobconfig_connectorrequest_changelist"
    )
    return HttpResponseRedirect(redirect_to)


class ConnectorRequestForm(forms.ModelForm):
    class Meta:
        model = ConnectorRequest
        fields = ["account"]
        widgets = {
            "account": autocomplete.ModelSelect2(
                url="coreobjects-autocomplete",
                forward=[
                    (forward.Const(Account.__coreobjects_type__, "type")),
                ],
            ),
        }


@admin.register(ConnectorRequest)
class ConnectorRequestAdmin(BaseAdmin, DynamicArrayMixin):
    form = ConnectorRequestForm
    fieldsets = [
        (
            "Attributes",
            {
                "fields": (
                    "id",
                    "account",
                    "type",
                    "name",
                    "login_url",
                    "username",
                    "converted_to_connector",
                    "password",
                    "converted_to_job",
                    "is_deleted",
                ),
            },
        ),
        (
            "Creation / Updation info",
            {
                "fields": (
                    "last_modified_date",
                    "last_modified_user",
                    "created_date",
                    "created_user",
                ),
            },
        ),
    ]

    @action_short_description("Convert to job")
    def convert_to_job(self, request, connectorrequest_id: Union[str, QuerySet]):
        """
        :param request: Request
        :param connectorrequest_id: This can be queryset (if called from django admin list action) or str if called
                       from django `admin/jobconfig/connectorrequest/<connectorrequest_id>/` view
        :return:
        """
        queryset = (
            ConnectorRequest.objects.filter(pk=connectorrequest_id)
            if isinstance(connectorrequest_id, str)
            else connectorrequest_id
        )
        return convert_connector_request_to_job(self, request, queryset)

    search_fields = (
        "id",
        "name",
        "username",
        "login_url",
        "account__display_name",
        "account__remote_id",
    )
    list_display = (
        "id",
        "account_name",
        "is_deleted",
        "name",
        "username",
        "login_url",
        "converted_to_connector",
    )
    list_filter = (
        "is_deleted",
        "type",
        "account",
    )
    ordering = ("-created_date",)
    actions = [convert_to_job]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:  # editing an existing object
            return readonly_fields + ["account"]
        return readonly_fields

    def get_autocomplete_fields(self, request):
        return ["account"]

    @classmethod
    def account_name(cls, obj):
        return f"{obj.account.display_name}" if obj.account else None
