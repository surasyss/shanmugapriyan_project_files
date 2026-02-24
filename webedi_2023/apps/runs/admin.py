import os
import tempfile

import humanize
import textract
from admin_auto_filters.filters import AutocompleteFilter
from django import forms
from django.conf.urls import url
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.contrib.postgres import fields as pg_fields
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import IntegrityError
from django.db.models import Q
from django.db.models.expressions import RawSQL
from django.http import HttpResponseRedirect, JsonResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django_json_widget.widgets import JSONEditorWidget
from spices.django3.admin.utils import action_short_description, to_link, BaseAdmin
from spices.django3.issues.models import IssueActionChoice
from spices.documents import DocumentType
from spices.services import ContextualError
from textract.exceptions import ExtensionNotSupported

from apps.adapters import file_actions
from apps.adapters.engine import post_process_discovered_files
from apps.adapters.file_actions import SkipProcessing
from apps.definitions.models import ConnectorType, Connector
from apps.error_codes import ErrorCode
from apps.jobconfig.models import FileDiscoveryActionType, Job
from apps.runs import LOGGER
from apps.runs.models import (
    Run,
    DiscoveredFile,
    CheckRun,
    DiscoveredEntity,
    ExportRequest,
    RunStatus,
    RunCancellationReason,
    RunCreatedVia,
    FileFormat,
    get_extension,
)
from apps.utils.papertrail_api import get_papertrail_logs
from integrator import settings


@action_short_description("Send connector requests enabled emails")
def trigger_vc_emails(modeladmin: admin.ModelAdmin, request, queryset):
    from apps.runs import tasks  # pylint: disable=import-outside-toplevel,cyclic-import

    ignored = []
    email_sent = []
    for run in queryset.all().distinct("job").order_by("job_id"):
        # pylint: disable=no-member
        if run.status == RunStatus.FAILED.ident:
            tasks.send_email.delay(
                run.get_email_content("connector-request-enabled-failure")
            )
            email_sent.append(run.job)
        # pylint: disable=no-member
        elif run.status == RunStatus.SUCCEEDED.ident:
            tasks.send_email.delay(
                run.get_email_content("connector-request-enabled-success")
            )
            email_sent.append(run.job)
        else:
            ignored.append(run.job)

    message = (
        f"Connector request enabling emails sent successfully : "
        f'{",".join(f"{str(job)}({str(job.get_created_user_email())})" for job in email_sent)}'
    )
    level = messages.INFO
    if ignored:
        level = messages.WARNING
        message = (
            f"{message} (ignored : "
            f'{",".join(f"{str(job)}({str(job.get_created_user_email())})" for job in ignored)})'
        )

    modeladmin.message_user(request, message=mark_safe(message), level=level)


@action_short_description("Mark As Complete")
def mark_as_complete(modeladmin: admin.ModelAdmin, request, queryset):
    ignored = []
    updated = []
    for run in queryset.all():
        try:
            run.record_success()
            updated.append(run)
        except ValidationError:
            ignored.append(run)
            continue

    message = f'Run marked as completed : {",".join(str(run) for run in updated)}'
    level = messages.INFO
    if ignored:
        level = messages.WARNING
        message = message + f' (ignored {",".join(str(run) for run in ignored)})'

    modeladmin.message_user(request, message=mark_safe(message), level=level)


@action_short_description("Trigger Now")
def trigger_now(modeladmin: admin.ModelAdmin, request, queryset):
    ignored = []
    created = []
    for run in queryset.all():
        try:
            run.execute_async()
            created.append(run)
        except ValidationError:
            ignored.append(run)
            continue

    message = f'Run Triggered Asynchronously : {",".join(str(run) for run in created)}'
    level = messages.INFO
    if ignored:
        level = messages.WARNING
        message = message + f' (ignored {",".join(str(run) for run in ignored)})'

    modeladmin.message_user(request, message=mark_safe(message), level=level)


@action_short_description("Force reset")
def force_reset(modeladmin: admin.ModelAdmin, request, queryset):
    LOGGER.info(f"User {request.user.id} requested forced reset for selected Runs")
    runs = queryset.all()
    for run in runs:  # type: Run
        run.reset()
        LOGGER.info(f"Force reset Run {run.id}")

    modeladmin.message_user(
        request,
        f'Forcefully reset runs successfully : {",".join(str(run) for run in runs)}',
    )


@action_short_description("Force cancel")
def force_cancel(modeladmin: admin.ModelAdmin, request, queryset):
    cancel_reason = request.POST.get("cancel_reason")
    cancel_reason_text = request.POST.get("cancel_reason_text")
    LOGGER.info(f"User {request.user.id} requested forced cancel for selected Runs")
    created = []
    ignored = []
    runs = queryset.all()
    for run in runs:  # type: Run
        try:
            run.cancel(cancel_reason, cancel_reason_text, request.user)
            created.append(run)
        except ValidationError as exc:
            LOGGER.warning(
                f"Exception occurred while cancelling {run.id} : {exc.messages}"
            )
            ignored.append(run)

    message = f'Cancelled runs successfully : {",".join(str(run) for run in created)}'
    level = messages.INFO
    if ignored:
        level = messages.WARNING
        message = message + f' (ignored {",".join(str(run) for run in ignored)})'

    modeladmin.message_user(request, message=mark_safe(message), level=level)
    # if the user was on a page with filters set, we want to send the user back to the same page
    redirect_to = request.META.get("HTTP_REFERER") or reverse(
        "admin:runs_run_changelist"
    )
    return HttpResponseRedirect(redirect_to)


class DiscoveredFileInline(admin.TabularInline):
    model = DiscoveredFile
    extra = 0
    can_delete = False
    fields = [
        "connector",
        "original_filename",
        "document_type",
        "file_format",
        "downloaded_successfully",
        "piq_upload_id",
        "piq_container_id",
        "url",
        "original_download_url",
    ]
    readonly_fields = [f.name for f in DiscoveredFile._meta.concrete_fields]
    ordering = ("-created_date",)

    def has_add_permission(self, request, obj=None):
        return False


class DiscoveredEntityInline(admin.TabularInline):
    model = DiscoveredEntity
    extra = 0
    can_delete = False
    fields = ["type", "export_request", "source_entity_id", "created_date"]
    readonly_fields = [f.name for f in DiscoveredEntity._meta.concrete_fields]
    ordering = ("-created_date",)

    def has_add_permission(self, request, obj=None):
        return False


class ExportRequestInline(admin.TabularInline):
    model = ExportRequest
    extra = 0
    can_delete = False
    fields = [
        "http_request_method",
        "http_request_url",
        "http_response_code",
        "success",
    ]
    readonly_fields = [f.name for f in ExportRequest._meta.concrete_fields]
    ordering = ("-created_date",)

    def has_add_permission(self, request, obj=None):
        return False


class CheckRunInline(admin.TabularInline):
    model = CheckRun
    extra = 0
    can_delete = False
    fields = [
        "check_run_id",
        "is_checkrun_success",
        "is_patch_success",
    ]
    readonly_fields = [f.name for f in CheckRun._meta.concrete_fields]
    ordering = ("-created_date",)

    def has_add_permission(self, request, obj=None):
        return False


class FailureIssueFilter(SimpleListFilter):
    title = "Failure type"
    parameter_name = "failure_type"

    def lookups(self, request, model_admin):
        return (
            ("auth_failure", "Authentication Failure"),
            ("others", "Others Except Authentication Failure"),
        )

    def queryset(self, request, queryset):
        if self.value() == "auth_failure":
            return queryset.filter(failure_issue__code="intgrt.auth_failed.web")
        if self.value() == "others":
            return queryset.exclude(failure_issue__code="intgrt.auth_failed.web")
        return queryset


class HasDiscoveredFiles(SimpleListFilter):
    title = "Run has discovered files?"
    parameter_name = "has_dfs"

    def lookups(self, request, model_admin):
        return (("Yes", "Run has discovered files"),)

    def queryset(self, request, queryset):
        if self.value() == "Yes":
            return queryset.exclude(discovered_files__isnull=True)
        return queryset


class JobListFilter(admin.SimpleListFilter):
    title = "Job"
    parameter_name = "filter_job_id"

    def lookups(self, request, model_admin):
        return (
            (
                job.id,
                str(job),
            )
            for job in Job.objects.all().select_related("account", "connector")
        )

    def queryset(self, request, queryset):
        return queryset.filter(job__id=self.value()) if self.value() else queryset


class RunJobListFilter(admin.SimpleListFilter):
    title = "Job"
    parameter_name = "filter_job_id"

    def lookups(self, request, model_admin):
        return (
            (
                job.id,
                str(job),
            )
            for job in Job.objects.filter(enabled=True).select_related(
                "account", "connector"
            )
        )

    def queryset(self, request, queryset):
        return queryset.filter(run__job__id=self.value()) if self.value() else queryset


class ConnectorNameListFilter(admin.SimpleListFilter):
    title = "Connector"
    parameter_name = "filter_connector_id"

    def lookups(self, request, model_admin):
        return (
            (
                con["id"],
                con["name"],
            )
            for con in Connector.objects.values("id", "name").filter(enabled=True)
        )

    def queryset(self, request, queryset):
        return (
            queryset.filter(job__connector__id=self.value())
            if self.value()
            else queryset
        )


class CRConnectorNameListFilter(admin.SimpleListFilter):
    title = "Connector"
    parameter_name = "filter_connector_id"

    def lookups(self, request, model_admin):
        return (
            (
                con["id"],
                con["name"],
            )
            for con in Connector.objects.values("id", "name").filter(enabled=True)
        )

    def queryset(self, request, queryset):
        return (
            queryset.filter(run__job__connector__id=self.value())
            if self.value()
            else queryset
        )


class AdapterCodeListFilter(admin.SimpleListFilter):
    title = "Adapter Code"
    parameter_name = "filter_adapter_code"

    def lookups(self, request, model_admin):
        return (
            (
                con["adapter_code"],
                con["adapter_code"],
            )
            for con in Connector.objects.values("adapter_code")
            .distinct()
            .filter(enabled=True)
        )

    def queryset(self, request, queryset):
        return (
            queryset.filter(job__connector__adapter_code=self.value())
            if self.value()
            else queryset
        )


class DFAdapterCodeListFilter(admin.SimpleListFilter):
    title = "Adapter Code"
    parameter_name = "filter_adapter_code"

    def lookups(self, request, model_admin):
        return (
            (
                con["adapter_code"],
                con["adapter_code"],
            )
            for con in Connector.objects.values("adapter_code")
            .distinct()
            .filter(enabled=True)
        )

    def queryset(self, request, queryset):
        return (
            queryset.filter(connector__adapter_code=self.value())
            if self.value()
            else queryset
        )


def original_file_validator(value):
    if value.size == 0:
        raise ValidationError("Size of file is Zero. Invalid Invoice file!!!")


class UploadInvoicesForm(forms.Form):
    original_file = forms.FileField(
        required=True,
        validators=[original_file_validator],
        widget=forms.ClearableFileInput(attrs={"allow_multiple_selected": True}),
    )


@admin.register(Run)
class RunAdmin(BaseAdmin):
    connector_link = to_link("job__connector", short_description="Connector Link")
    job_link = to_link("job", short_description="Job Link")
    failure_issue_link = to_link(
        "failure_issue", short_description="Failure Issue Link"
    )

    list_display = (
        "id2",
        "created_date",
        "action",
        "created_via",
        "job_link",
        "status",
        "execution_duration",
        "action_required",
        "failure_detail",
    )
    list_display_links = ("id2", "created_date")
    list_filter = (
        "status",
        "dry_run",
        "is_manual",
        HasDiscoveredFiles,
        FailureIssueFilter,
        "action",
        "created_via",
        "job__connector__type",
        AdapterCodeListFilter,
        ConnectorNameListFilter,
        JobListFilter,
    )
    search_fields = ("id", "action", "created_date", "job__id")
    ordering = ("-created_date",)

    fieldsets = [
        (
            "Quick Links",
            {
                "fields": (
                    "connector_link",
                    "job_link",
                    "aws_batch_job_logs_link",
                    "papertrail_log_url_shortcut",
                    "shortcuts",
                ),
            },
        ),
        (
            "Attributes",
            {
                "fields": (
                    "id",
                    "job",
                    "created_via",
                    "is_manual",
                    "request_parameters",
                    "canceled_reason",
                    "canceled_reason_text",
                    "canceled_by_user",
                    "last_modified_date",
                    "last_modified_user",
                    "created_date",
                    "created_user",
                ),
            },
        ),
        (
            "Execution Status",
            {
                "fields": (
                    "status",
                    "aws_batch_job_id",
                    "execution_duration",
                    "execution_end_ts",
                    "execution_start_ts",
                    "failure_issue_link",
                ),
            },
        ),
    ]

    @action_short_description("Cancel run")
    def cancel_run_with_confirmation(self, request, run_id):
        """
        :param request: Request
        :param run_id: This can be queryset (if called from django admin list action) or str if called
                       from django `admin/runs/run/<run_id>/cancel/` view
        :return:
        """
        queryset = Run.objects.filter(pk=run_id) if isinstance(run_id, str) else run_id
        if request.POST.get("post"):
            queryset = Run.objects.filter(pk__in=request.POST.getlist("run_object_ids"))
            return force_cancel(self, request, queryset)

        if not isinstance(run_id, str):
            object_id = queryset[0].id
            context = {
                "title": "Cancel run",
                "to_be_canceled_objects": queryset,
                "action_checkbox_name": "cancel-run",
                "cancel_reasons": RunCancellationReason.as_ident_message_dict(),
                "opts": Run._meta,
                "object_id": object_id,
                "site_header": settings.DJANGO_ADMIN_SITE_HEADER,
            }
            return TemplateResponse(
                request, "runs/cancel_run_confirmation.html", context
            )
        return None

    @staticmethod
    def papertrail_log_url_shortcut(obj: Run):
        if not obj:
            return None

        papertrail_url = f"https://my.papertrailapp.com/systems/{settings.PAPERTRAIL_SYSTEM_ID}/events?q={obj.id}"
        try:
            logs = get_papertrail_logs(
                settings.PAPERTRAIL_API_TOKEN, settings.PAPERTRAIL_SYSTEM_ID, obj.id
            )
            if not logs:
                return format_html(
                    f"No logs exists at papertrail for this <a href='{papertrail_url}'>run.</a>"
                )

            rows = ""
            for log in logs:
                if message := log.get("message"):
                    received_at = log["display_received_at"]
                    rows = rows + f"<tr><td>{received_at}</td><td>{message}</td></tr>"

            html = f"""
            <div style='max-height: 220px;scroll-behavior: smooth;overflow-y: scroll;'>
                <table>
                    <tr><th>Time</th><th>Message</th></tr>
                    {rows}
                </table>
            </div>
            <div style='margin-top:2em;'>
                <a style='padding:8px' href='{papertrail_url}'>Check more at Papertrail</a>
            </div>
            """
            return format_html(html)
        except KeyError:
            return format_html(
                f"No logs exists at papertrail for this <a href='{papertrail_url}'>run.</a>"
            )

    actions = [
        trigger_now,
        force_reset,
        cancel_run_with_confirmation,
        trigger_vc_emails,
        mark_as_complete,
    ]

    inlines = [
        DiscoveredFileInline,
        CheckRunInline,
        DiscoveredEntityInline,
        ExportRequestInline,
    ]
    formfield_overrides = {
        pg_fields.JSONField: {"widget": JSONEditorWidget},
    }

    def manual_invoice_run_list_view(self, request):
        context = dict(
            self.admin_site.each_context(request),
            title="Runs",
            site_header=settings.DJANGO_ADMIN_SITE_HEADER,
        )
        # pylint: disable=no-member
        run_list = Run.objects.filter(
            is_manual=True,
            status__in=[RunStatus.CREATED.ident, RunStatus.STARTED.ident],
        )
        context.update(
            {
                "runs": run_list,
            }
        )
        return TemplateResponse(request, "runs/manual_invoice_runs.html", context)

    @staticmethod
    def mark_run_as_started_view(request, **kwargs):
        run = Run.objects.get(id=kwargs["run_id"])
        if request.POST:
            try:
                run.last_modified_user = request.user
                if request.POST.get("start_run", "false") == "true":
                    run.record_execution_start()
                    return JsonResponse(
                        status=200, data={"message": "Run started successfully."}
                    )
                return JsonResponse(status=400, data={"message": "Invalid request!!"})

            except Exception as exc:  # pylint: disable=broad-except
                return JsonResponse(
                    status=400,
                    data={
                        "message": f"Failed while starting run with exception : {exc}",
                    },
                )
        return JsonResponse(status=400, data={"message": "Invalid request!!"})

    def manual_invoice_download_view(self, request, **kwargs):
        context = dict(
            self.admin_site.each_context(request),
            title="Manual invoice download",
            site_header=settings.DJANGO_ADMIN_SITE_HEADER,
        )
        run = Run.objects.get(id=kwargs["run_id"])
        connector = run.job.connector
        discovered_files = DiscoveredFile.objects.filter(run__job=run.job).order_by(
            "-created_date"
        )[:5]
        context.update(
            {
                "run": run,
                "discovered_files": discovered_files,
                "connector": connector,
                "file_format": connector.get_supported_invoice_format,
                "vpn_required": connector.get_custom_properties.get(
                    "vpn_required", False
                ),
                "start_date": run.request_parameters["start_date"],
                "end_date": run.request_parameters["end_date"],
            }
        )
        if request.POST:
            try:
                if (
                    "auth_failure_issue" in request.POST
                    and request.POST["auth_failure_issue"] == "on"
                ):
                    # pylint: disable=no-member
                    raise ContextualError(
                        code=ErrorCode.AUTHENTICATION_FAILED_WEB.ident,
                        message=ErrorCode.AUTHENTICATION_FAILED_WEB.message.format(
                            username=run.job.username
                        ),
                        params={"error_msg": "Raised while downloading manually."},
                    )
                if (
                    "accessing_site_issue_checkbox" in request.POST
                    and request.POST["accessing_site_issue_checkbox"] == "on"
                ):
                    raise ContextualError(
                        code=ErrorCode.EXTERNAL_UPSTREAM_UNAVAILABLE.ident,  # pylint: disable=no-member
                        message=ErrorCode.EXTERNAL_UPSTREAM_UNAVAILABLE.message,  # pylint: disable=no-member
                        params={"error_msg": "Raised while downloading manually."},
                    )
                run.record_success()

                LOGGER.warning(
                    f"[tag:IDV200][run:{run.id}] Processing discovered files"
                )
                post_process_discovered_files(run)

                redirect_to = reverse("admin:manual-invoice-run-list")
                return HttpResponseRedirect(redirect_to)
            except ContextualError as exc:
                run.record_failure(exc)
                redirect_to = reverse("admin:manual-invoice-run-list")
                return HttpResponseRedirect(redirect_to)
            except Exception:  # pylint: disable=broad-except
                redirect_to = reverse("admin:manual-invoice-run-list")
                return HttpResponseRedirect(redirect_to)

        return TemplateResponse(request, "runs/manual_invoice_download.html", context)

    def invoice_download_view(self, request, **kwargs):
        context = dict(
            self.admin_site.each_context(request),
            title="invoice download",
            site_header=settings.DJANGO_ADMIN_SITE_HEADER,
        )
        run = Run.objects.get(id=kwargs["run_id"])
        context.update(
            {
                "run": run,
            }
        )
        if request.POST:
            try:
                form = UploadInvoicesForm(request.POST, request.FILES)
                if form.is_valid():
                    filename = form.cleaned_data["original_file"].name
                    extension = get_extension(filename)
                    extension = extension and extension.lower()
                    supported_format = str(
                        run.job.connector.get_supported_invoice_format
                    ).lower()
                    if extension != supported_format:
                        raise ValidationError(
                            f"This job does not support '{extension}' file format, "
                            f"please upload '{supported_format}' format."
                        )

                    discovered_file = DiscoveredFile.build_unique(
                        run,
                        reference_code="",
                        document_type=DocumentType.INVOICE.ident,  # pylint: disable=no-member
                        file_format=extension,
                        # Not asking DE users to add download url as well, and as its not-null-not-blank field
                        # passing null in text.
                        original_download_url="",
                        original_filename=filename,
                        document_properties={},
                    )

                    u_file_contents = form.cleaned_data["original_file"].file.read()
                    with tempfile.NamedTemporaryFile(
                        delete=True, suffix=f".{extension}"
                    ) as temp:
                        temp.write(u_file_contents)
                        temp.flush()
                        discovered_file.save_content(
                            temp.name,
                            compute_extracted_text_hash=run.job.connector.get_custom_properties.get(
                                "compute_extracted_text_hash", True
                            ),
                        )
                        LOGGER.warning(
                            f"[tag:IDV100][run:{run.id}] Create a discovered file - {discovered_file.id}"
                        )
                        discovered_file.downloaded_successfully = True
                        discovered_file.save()

                    return JsonResponse(
                        status=200,
                        data={
                            "message": f"Saved invoice successfully.",
                            "disc_file_id": discovered_file.id,
                        },
                    )

                return JsonResponse(
                    status=400,
                    data={
                        "message": "Failed while validating form.",
                        "errors": form.errors,
                    },
                )
            except IntegrityError:
                LOGGER.warning(
                    f"[tag:IDV][run:{run.id}] Invoice is already downloaded - Hence skipping"
                )
                return JsonResponse(
                    status=200,
                    data={
                        "message": f"Invoice is already downloaded.",
                    },
                )
            except ValidationError as exc:
                return JsonResponse(
                    status=400,
                    data={
                        "message": f"Failed : {exc.message}",
                    },
                )
            except Exception as exc:  # pylint: disable=broad-except
                LOGGER.warning(
                    f"[tag:IDV][run:{run.id}] Failed while saving invoice with exception : {exc}"
                )

                return JsonResponse(
                    status=400,
                    data={
                        "message": f"Failed while saving invoice with exception : {exc}",
                    },
                )

        return True

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            url(
                r"^(?P<run_id>.+)/cancel/$",
                self.admin_site.admin_view(self.cancel_run_with_confirmation),
                name="cancel-run-action",
            ),
            url(
                r"^manual/$",
                self.admin_site.admin_view(self.manual_invoice_run_list_view),
                name="manual-invoice-run-list",
            ),
            url(
                r"^manual/(?P<run_id>.+)/$",
                self.admin_site.admin_view(self.manual_invoice_download_view),
                name="manual-invoice-download",
            ),
            url(
                r"^invoice/(?P<run_id>.+)/$",
                self.admin_site.admin_view(self.invoice_download_view),
                name="invoice-download",
            ),
            url(
                r"^start/(?P<run_id>.+)/$",
                self.admin_site.admin_view(self.mark_run_as_started_view),
                name="mark-run-started",
            ),
        ]
        return custom_urls + urls

    def lookup_allowed(self, lookup, value):
        if lookup in ["job__connector"]:
            return True
        return super().lookup_allowed(lookup, value)

    @staticmethod
    def id2(obj):
        """Id along with DryRun pill"""
        pill = ' <span style="background:gold;">(Dry Run)</span>' if obj.dry_run else ""
        manual = (
            ' <span style="background:#b82cff4f;">(Manual)</span>'
            if obj.is_manual
            else ""
        )
        return format_html(f"{obj.id}{pill}{manual}")

    id2.allow_tags = True

    @staticmethod
    def execution_duration(obj):
        """Human readable execution duration"""
        if not obj.execution_start_ts or not obj.execution_end_ts:
            return None

        readable = humanize.naturaldelta(obj.execution_end_ts - obj.execution_start_ts)
        if obj.execution_end_ts < obj.execution_start_ts:
            readable = f"(minus) {readable}"

        return readable

    def get_inline_instances(self, request, obj=None):
        inlines = self.inlines

        if not obj or not obj.pk:
            inlines = []

        # pylint: disable=no-member
        if obj and obj.job.connector.type == ConnectorType.VENDOR.ident:
            inlines = [
                DiscoveredFileInline,
            ]

        if obj and obj.job.connector.type == ConnectorType.ACCOUNTING.ident:
            inlines = [
                CheckRunInline,
                DiscoveredEntityInline,
                ExportRequestInline,
            ]

        return [inline(self.model, self.admin_site) for inline in inlines]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super(RunAdmin, self).get_readonly_fields(request, obj)
        readonly_fields = readonly_fields + [
            "id2",
            "execution_duration",
            "aws_batch_job_logs_link",
            "shortcuts",
            "canceled_reason",
            "connector_link",
            "job_link",
            "failure_issue_link",
            "canceled_by_user",
            "canceled_reason_text",
            "status",
            "execution_start_ts",
            "execution_end_ts",
            "failure_issue",
            "action_required",
            "created_via",
            "papertrail_log_url_shortcut",
        ]
        if obj:  # editing an existing object
            return readonly_fields + ["job"]
        return readonly_fields

    def get_autocomplete_fields(self, request):
        field_names = []
        return field_names

    @staticmethod
    def failure_detail(obj: Run):
        if not obj.failure_issue:
            return "-"

        error_code = obj.failure_issue.code
        link_url = reverse("admin:issues_issue_change", args=[obj.failure_issue_id])
        error_code_link = f'<a href="{link_url}">{error_code}</a>'
        return format_html(error_code_link)

    failure_detail.allow_tags = True

    @staticmethod
    def action_required(obj: Run):
        if not obj.failure_issue:
            return "-"

        color = "red"
        bg_color = "none"
        action = "Unexpected error"

        rule = obj.failure_issue.get_or_create_rule()
        if rule and rule.action_required:
            color = "#333"
            bg_color = (
                "gold"
                if rule.action_required == IssueActionChoice.OPS_INPUT
                else "none"
            )
            action = rule.action_required.message

        return format_html(
            f'<span style="background: {bg_color}; color: {color}">{action}</span>'
        )

    action_required.allow_tags = True

    @staticmethod
    def shortcuts(obj):
        if not obj or not obj.id:
            return "-"

        discoveredrile_url = (
            f"{reverse('admin:runs_discoveredfile_changelist')}?run={obj.id}"
        )
        checkruns_url = f"{reverse('admin:runs_checkrun_changelist')}?run={obj.id}"

        return format_html(
            f"""
                <div>
                    <span><a href="{discoveredrile_url}">Related Discovered Files</a></span>
                    &nbsp;&nbsp;|&nbsp;&nbsp;
                    <span><a href="{checkruns_url}">Related Check Runs</a></span>
                </div>
            """
        )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("job", "failure_issue")
            .prefetch_related("job__connector", "job__account")
        )


@action_short_description("Create PIQ Invoice")
def create_piq_invoice(modeladmin: admin.ModelAdmin, request, queryset):
    message = "Created PIQ invoice for selected discovered file(s)"
    return _post_process_discovered_file(modeladmin, request, queryset, message)


@action_short_description("Post-process DF")
def post_process_df(modeladmin: admin.ModelAdmin, request, queryset):
    message = "Post-processed selected discovered file(s)"
    return _post_process_discovered_file(modeladmin, request, queryset, message)


def _post_process_discovered_file(
    modeladmin: admin.ModelAdmin, request, queryset, message
):
    LOGGER.info(
        f"User {request.user.id} requested creating PIQ invoices for selected discovered files"
    )

    for discovered_file in queryset.all():  # type: DiscoveredFile
        # we call a private method here assuming that the django admin user called this action for the correct scenario
        # noinspection PyUnresolvedReferences,PyProtectedMember
        file_actions.factory(discovered_file).execute()

    modeladmin.message_user(request, message)


class UploadSetFilter(SimpleListFilter):
    title = "UploadId Set?"
    parameter_name = "is_uploadid_set"

    def queryset(self, request, queryset):
        if value := self.value():
            if value.lower() == "yes":
                queryset = queryset.filter(piq_upload_id__isnull=False)
            elif value.lower() == "no":
                queryset = queryset.filter(piq_upload_id__isnull=True)

        return queryset

    def lookups(self, request, model_admin):
        return (
            ("yes", "Set"),
            ("no", "Not Set"),
        )


class ContainerCreatedFilter(SimpleListFilter):
    title = "Container Created?"
    parameter_name = "is_container_created"

    def queryset(self, request, queryset):
        if value := self.value():
            if value.lower() == "yes":
                queryset = queryset.filter(piq_container_id__isnull=False)
            elif value.lower() == "no":
                queryset = queryset.filter(piq_container_id__isnull=True)

        return queryset

    def lookups(self, request, model_admin):
        return (
            ("yes", "Created"),
            ("no", "Not Created"),
        )


class SuppressInvoicesFilter(SimpleListFilter):
    title = "Suppress Invoices?"
    parameter_name = "suppress_invoices"

    def queryset(self, request, queryset):
        if value := self.value():
            if value.lower() == "yes":
                queryset = queryset.filter(
                    run__request_parameters__suppress_invoices=True
                )
            elif value.lower() == "no":
                queryset = queryset.filter(
                    Q(run__request_parameters__suppress_invoices__isnull=True)
                    | Q(run__request_parameters__suppress_invoices=False)
                )

        return queryset

    def lookups(self, request, model_admin):
        return (
            ("yes", "yes"),
            ("no", "no"),
        )


@admin.register(DiscoveredFile)
class DiscoveredFileAdmin(BaseAdmin):
    connector_link = to_link("run__job__connector", short_description="Connector Link")
    job_link = to_link("run__job", short_description="Job Link")
    run_link = to_link("run", short_description="Run Link")

    search_fields = (
        "id",
        "run__id",
        "original_filename",
        "connector__name",
        "original_download_url",
    )
    list_select_related = (
        "run",
        "run__job",
        "connector",
    )
    list_display = (
        "id",
        to_link("run"),
        to_link("connector"),
        "created_date",
        "original_filename",
        "document_metadata",
        "processing_status",
    )
    list_filter = (
        "downloaded_successfully",
        "file_format",
        UploadSetFilter,
        ContainerCreatedFilter,
        SuppressInvoicesFilter,
        "document_type",
        "run__is_manual",
        DFAdapterCodeListFilter,
        RunJobListFilter,
    )
    ordering = ("-created_date",)

    actions = [
        create_piq_invoice,
        post_process_df,
    ]

    fieldsets = [
        (
            "Quick Links",
            {
                "fields": (
                    "connector_link",
                    "job_link",
                    "run_link",
                ),
            },
        ),
        (
            "Attributes",
            {
                "fields": (
                    "id",
                    "run",
                    "connector",
                    "original_file",
                    "original_filename",
                    "original_download_url",
                    "content_hash",
                    "extracted_text_hash",
                    "file_format",
                    "document_type",
                    "document_properties",
                    "downloaded_successfully",
                    "downloaded_at",
                    "piq_upload_id",
                    "piq_container_id",
                    "piq_container_link",
                ),
            },
        ),
        (
            "Creation / Updation Info",
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

    formfield_overrides = {
        pg_fields.JSONField: {"widget": JSONEditorWidget},
    }

    def get_queryset(self, request):
        qs = (
            super()
            .get_queryset(request=request)
            .prefetch_related(
                "connector",
                "connector__document_discovery_actions",
                "run",
                "run__job",
                "run__job__document_discovery_actions",
            )
        )
        return qs

    # pylint: disable=no-self-use
    # noinspection PyMethodMayBeStatic
    def document_metadata(self, obj):
        # <div><strong>Content Hash</strong>: {obj.content_hash if obj.content_hash else "-"}</div>
        return format_html(
            f"""
            <div>
                <div><strong>Document Type</strong>: {obj.document_type}</div>
                <div><strong>File Format</strong>&nbsp;&nbsp;: {obj.file_format}</div>
            </div>
            """
        )

    # noinspection PyMethodMayBeStatic
    def processing_status(self, obj):  # pylint: disable=too-many-branches
        # suppress_invoices
        suppress_invoices = ""
        if obj.run.request_parameters.get("suppress_invoices", False) is True:
            suppress_invoices = "Discovered File is from a run which was configured to not create invoices"

        if obj.downloaded_successfully is True:
            retrieved = '<img src="/static/admin/img/icon-yes.svg" alt="True">'
        elif obj.downloaded_successfully is False:
            retrieved = '<img src="/static/admin/img/icon-no.svg" alt="True">'
        else:
            retrieved = '<img src="/static/admin/img/icon-unknown.svg" alt="True">'

        saved = "NA"
        _url = obj.file_url
        if obj.downloaded_successfully:
            if _url:
                saved = f'Yes, (<a href="{_url}" target="_blank">Download Link</a>)'
            else:
                saved = "Could not save"

        if obj.piq_container_id:
            piq_container_url = (
                settings.PIQ_CORE_CLIENT.get_invoice_container_admin_url(
                    obj.piq_container_id
                )
            )
            invoice_created = (
                f'<a href="{piq_container_url}" '
                f'target="_blank">{obj.piq_container_id}</a>'
            )
        else:
            invoice_created = "-"

        misconfiguration_warning = ""

        fda = obj.discovery_action_for_admin
        if (
            not fda or fda.action_type == FileDiscoveryActionType.NONE.ident
        ):  # pylint: disable=no-member
            misconfiguration_warning = (
                '<div style="color: red;">'
                "FileDiscoveryAction is not configured, "
                "creating invoice will have no effect</div>"
            )

        suppress_invoices_html = (
            f"<div><strong>Suppress Invoices</strong>: " f"{suppress_invoices}</div>"
            if suppress_invoices
            else ""
        )
        return format_html(
            f"""
            <div>
                <div><strong>Retrieved</strong>: {retrieved}</div>
                <div><strong>Saved to S3</strong>: {saved}</div>
                {suppress_invoices_html}
                <div><strong>PIQ Upload ID</strong>: {obj.piq_upload_id or "-"}</div>
                <div><strong>PIQ Container</strong>: {invoice_created}</div>
                {misconfiguration_warning}
            </div>
            """
        )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super(DiscoveredFileAdmin, self).get_readonly_fields(
            request, obj
        )
        readonly_fields += [
            "connector_link",
            "job_link",
            "run_link",
            "piq_container_link",
        ]

        if obj:  # editing an existing object
            readonly_fields += [
                "connector",
                "run",
                "original_filename",
                "original_download_url",
                "content_hash",
                "extracted_text_hash",
                "downloaded_successfully",
                "downloaded_at",
            ]
        return readonly_fields

    def get_autocomplete_fields(self, request):
        field_names = []
        return field_names

    @staticmethod
    def piq_container_link(obj):
        if not obj.piq_container_id:
            return "-"
        _url = settings.PIQ_CORE_CLIENT.get_invoice_container_admin_url(
            obj.piq_container_id
        )
        return format_html(f'<a href="{_url}">{_url}</a>')


@action_short_description("Mark as manually exported")
def mark_checkrun_as_manually_exported(modeladmin: admin.ModelAdmin, request, queryset):
    LOGGER.info(
        f"[tag:WARACRMME10] Processing user ({request.user.id}) request to mark checkruns as manually exported"
    )
    for checkrun in queryset.all():  # type: CheckRun
        LOGGER.info(
            f"[tag:WARACRMME20][user:{request.user.id}] Marking checkrun {checkrun.id} as manually exported"
        )
        checkrun.mark_as_manually_exported(request.user)

    modeladmin.message_user(
        request, "Selected checkruns were successfully marked as exported"
    )


@action_short_description("Update status on customer dashboard")
def notify_export_success(modeladmin: admin.ModelAdmin, request, queryset):
    LOGGER.info(
        f"[tag:WARACRUDS10] Processing user ({request.user.id}) request to notify export success"
    )
    for checkrun in queryset.all():  # type: CheckRun
        LOGGER.info(
            f"[tag:WARACRUDS20][user:{request.user.id}] Notify export success for checkrun {checkrun.id}"
        )
        checkrun.notify_export_success()

    modeladmin.message_user(
        request, "Selected checkruns were updated on the customer dashboard"
    )


@action_short_description("Disable CheckRuns")
def disable_check_runs(modeladmin: admin.ModelAdmin, request, queryset):
    LOGGER.info(f"[tag:CRADCR10] Disabling checkruns")
    for checkrun in queryset.all():  # type: CheckRun
        LOGGER.info(
            f"[tag:CRADCR20][CRID:{checkrun.check_run_id}][user:{request.user.id}] Disabling checkrun"
        )
        checkrun.is_disabled = True
        checkrun.save()

    modeladmin.message_user(request, "Selected checkruns are disabled successfully.")


@action_short_description("Enable CheckRuns")
def enable_check_runs(modeladmin: admin.ModelAdmin, request, queryset):
    LOGGER.info(f"[tag:CRAECR10] Eabling checkruns")
    check_run_id_list = queryset.filter(is_disabled=True).values_list(
        "check_run_id", flat=True
    )
    checkruns = CheckRun.objects.filter(
        check_run_id__in=check_run_id_list, is_disabled=True
    )
    for checkrun in checkruns:
        LOGGER.info(
            f"[tag:CRADCR20][CRID:{checkrun.check_run_id}][CID:{checkrun.id}] Enabling checkrun"
        )
        checkrun.is_disabled = False
        checkrun.save()
    modeladmin.message_user(request, "Selected checkruns are enabled successfully.")


@action_short_description("Export CheckRuns")
def export_check_runs(modeladmin: admin.ModelAdmin, request, queryset):
    LOGGER.info(f"[tag:CRAECR10][user:{request.user.id}] Exporting checkruns")
    ignored = []
    created = []
    run_data = dict()
    for checkrun in queryset.all():  # type: CheckRun
        run = checkrun.run
        check_run_id = str(checkrun.check_run_id)
        accounts = {
            key: val
            for key, val in run.request_parameters.get("accounting", {}).items()
            if check_run_id in key
        }
        if not accounts:
            ignored.append(check_run_id)
            continue
        if not run_data.get(run.job):
            run_data[run.job] = {}
        run_data[run.job].update(accounts)
        created.append(check_run_id)

    for job in run_data:
        run = job.last_run
        new_run = run.duplicate(
            created_via=RunCreatedVia.ADMIN_REQUEST,
            request_params=dict(version=1, accounting=run_data[job]),
        )
        new_run.execute_async()

    message = f'Triggered exporting for checkruns successfully : {",".join(str(checkrun) for checkrun in set(created))}'
    level = messages.INFO
    if ignored:
        level = messages.WARNING
        message = (
            message
            + f' (ignored {",".join(str(checkrun) for checkrun in set(ignored))})'
        )

    modeladmin.message_user(request, message=mark_safe(message), level=level)


class DisableCheckRunFilter(SimpleListFilter):
    title = "Disabled check runs?"
    parameter_name = "check_run"

    def queryset(self, request, queryset):
        if value := self.value():
            if value.lower() == "yes":
                queryset = queryset.filter(is_disabled=True)
            elif value.lower() == "no":
                queryset = queryset.exclude(is_disabled=True)
        return queryset

    def lookups(self, request, model_admin):
        return (
            ("yes", "Show disabled only"),
            ("no", "Show not disabled"),
        )


class ManualExporterFilter(AutocompleteFilter):
    title = "Manually Exported By"
    field_name = "manual_exporter_user"


@admin.register(CheckRun)
class CheckRunAdmin(BaseAdmin):
    run_link = to_link("run", short_description="Run Link")
    job_link = to_link("run__job", short_description="Job Link")
    connector_link = to_link("run__job__connector", short_description="Connector Link")
    manual_exporter_user_link = to_link(
        "manual_exporter_user", short_description="Manual Exporter Link"
    )
    failure_issue_link = to_link(
        "failure_issue", short_description="Failure Issue Link"
    )

    readonly_fields = [
        "connector_link",
        "job_link",
        "run_link",
        "manual_exporter_user_link",
        "failure_issue_link",  # FK links
        "export_success",  # computed fields
        "is_checkrun_success",
        "manual_exporter_user",
        "failure_issue",  # actual fields
    ]

    fieldsets = [
        (
            "Quick Links",
            {
                "fields": (
                    "connector_link",
                    "job_link",
                    "run_link",
                ),
            },
        ),
        (
            "Attributes",
            {
                "fields": (
                    "id",
                    "check_run_id",
                    "run",
                    "is_disabled",
                    "last_modified_date",
                    "last_modified_user",
                    "created_date",
                    "created_user",
                ),
            },
        ),
        (
            "Payment Status",
            {
                "fields": (
                    "export_success",
                    "is_checkrun_success",
                    "is_patch_success",
                    "failure_issue_link",
                    "manual_exporter_user_link",
                ),
            },
        ),
    ]

    list_display = (
        "check_run_id",
        "run_link",
        "job_link",
        "created_date",
        "export_success",
        "is_patch_success",
        "failure_detail",
    )
    list_filter = (
        "is_checkrun_success",
        "is_patch_success",
        DisableCheckRunFilter,
        ManualExporterFilter,
        "failure_issue__code",
        CRConnectorNameListFilter,
    )
    search_fields = (
        "id",
        "run__job__connector__name",
        "check_run_id",
    )
    ordering = ("-created_date",)

    actions = [
        mark_checkrun_as_manually_exported,
        notify_export_success,
        disable_check_runs,
        enable_check_runs,
        export_check_runs,
    ]

    def lookup_allowed(self, lookup, value):
        if lookup in ["run__job", "run__job__connector"]:
            return True
        return super().lookup_allowed(lookup, value)

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "manual_exporter_user",
                "run__job__account",
                "run__job__connector",
                "failure_issue",
            )
        )

    @staticmethod
    def export_success(obj: CheckRun):
        if obj.is_checkrun_success:
            html = '<img src="/static/admin/img/icon-yes.d2f9f035226a.svg" alt="True">'
            if obj.manual_exporter_user_id:
                link_url = reverse(
                    "admin:accounts_user_change", args=[obj.manual_exporter_user_id]
                )
                username = obj.manual_exporter_user.username
                html += f'<span style="background: gold;">Manual (<a href="{link_url}">{username}</a>)</span>'
        elif obj.is_checkrun_success is False:
            html = '<img src="/static/admin/img/icon-no.439e821418cd.svg" alt="False">'
        else:
            html = (
                '<img src="/static/admin/img/icon-unknown.a18cb4398978.svg" alt="None">'
            )

        return format_html(html)

    export_success.allow_tags = True

    @staticmethod
    def failure_detail(obj: CheckRun):
        if obj.is_checkrun_success:
            return "-"

        color = "red"
        bg_color = "none"
        action = "Unexpected error"
        error_code = error_code_link = ""

        if obj.failure_issue:
            link_url = reverse("admin:issues_issue_change", args=[obj.failure_issue_id])
            error_code = obj.failure_issue.code
            # if len(error_code) > 12:
            #     error_code = error_code[:9] + '...'

            error_code_link = f'<br/> (<a href="{link_url}">{error_code}</a>)'
            rule = obj.failure_issue.get_or_create_rule()
            if rule and rule.action_required:
                color = "#333"
                bg_color = (
                    "gold"
                    if rule.action_required == IssueActionChoice.OPS_INPUT
                    else "none"
                )
                action = rule.action_required.message

        return format_html(
            f'<span style="background: {bg_color}; color: {color}" title="{error_code}">{action}</span>'
            f"{error_code_link}"
        )

    failure_detail.allow_tags = True

    def get_readonly_fields(self, request, obj=None):
        self.readonly_fields = super(CheckRunAdmin, self).get_readonly_fields(
            request, obj
        )
        if obj:  # editing an existing object
            return self.readonly_fields + ["run", "check_run_id"]
        return self.readonly_fields

    def get_autocomplete_fields(self, request):
        return ["run"]


@admin.register(DiscoveredEntity)
class DiscoveredEntityAdmin(BaseAdmin):
    run_link = to_link("run", short_description="Run Link")
    connector_link = to_link("run__job__connector", short_description="Connector Link")
    export_request_link = to_link(
        "export_request", short_description="Export Request Link"
    )

    fields = [f.name for f in DiscoveredEntity._meta.concrete_fields]
    search_fields = (
        "id",
        "run__job__connector__name",
        "type",
        "source_entity_id",
    )
    list_display = (
        "id",
        "run_link",
        "connector_link",
        "type",
        "export_request_link",
        "created_date",
    )
    list_filter = (
        "run__job__connector",
        "type",
    )
    ordering = ("-created_date",)

    formfield_overrides = {
        pg_fields.JSONField: {"widget": JSONEditorWidget},
    }

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super(DiscoveredEntityAdmin, self).get_readonly_fields(
            request, obj
        )
        readonly_fields += [
            "connector_link",
            "job_link",
            "run_link",
            "export_request_link",
        ]
        if obj:  # editing an existing object
            return readonly_fields + ["run", "type"]
        return readonly_fields

    def get_autocomplete_fields(self, request):
        field_names = []
        return field_names


@admin.register(ExportRequest)
class ExportRequestAdmin(BaseAdmin):
    fields = [f.name for f in ExportRequest._meta.concrete_fields]
    search_fields = (
        "id",
        "run__job__connector__name",
    )
    list_display = (
        "id",
        to_link("run", short_description="Run"),
        "http_request_method",
        "success",
        "last_modified_date",
    )
    list_filter = (
        "success",
        "run__job__connector",
        "discovered_entities__type",
    )
    list_select_related = ["run"]
    ordering = ("-created_date",)

    formfield_overrides = {
        pg_fields.JSONField: {"widget": JSONEditorWidget},
    }

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super(ExportRequestAdmin, self).get_readonly_fields(
            request, obj
        )
        if obj:  # editing an existing object
            return readonly_fields + [
                "run",
                "http_request_method",
                "http_request_url",
                "http_response_code",
                "http_response_body",
            ]
        return readonly_fields

    def get_autocomplete_fields(self, request):
        field_names = []
        return field_names
