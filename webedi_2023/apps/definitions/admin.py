from typing import Union

from dal import autocomplete, forward
from django import forms
from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.db.models import Q, QuerySet
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.definitions import LOGGER
from apps.definitions.models import (
    Connector,
    ConnectorVendorInfo,
    ConnectorType,
    ConnectorCapability,
)
from apps.jobconfig.models import FileDiscoveryAction
from spices.django3.admin.utils import to_link, BaseAdmin, action_short_description
from spices.django3.coreobjects.models import Vendor, VendorGroup

_BACKLOG_ADAPTER_CODE = "backlog"


class BacklogFilter(SimpleListFilter):
    title = "Integration Status"
    parameter_name = "integration_status"

    _join_prefix = ""

    def queryset(self, request, queryset):
        if value := self.value():
            if value.lower() == "backlog":
                queryset = queryset.filter(
                    Q(**{f"{self._join_prefix}adapter_code": _BACKLOG_ADAPTER_CODE})
                )
            elif value.lower() == "integrated":
                queryset = queryset.exclude(
                    **{f"{self._join_prefix}adapter_code": _BACKLOG_ADAPTER_CODE}
                )

        return queryset

    def lookups(self, request, model_admin):
        return (
            ("Backlog", "Backlog"),
            ("Integrated", "Integrated"),
        )

    @staticmethod
    def new(join_prefix: str):
        class NewBacklogFilter(BacklogFilter):
            _join_prefix = join_prefix

        return NewBacklogFilter


class ConnectorCapabilityInline(admin.TabularInline):
    model = ConnectorCapability
    extra = 1
    fields = ["type", "supported_file_format"]
    ordering = ("type",)


class ConnectorVendorInfoForm(forms.ModelForm):
    class Meta:
        model = ConnectorVendorInfo
        fields = [
            "vendor_group",
            "vendor",
            "contains_support_document",
            "requires_account_number",
        ]
        widgets = {
            "vendor_group": autocomplete.ModelSelect2(
                url="coreobjects-autocomplete",
                forward=[
                    (forward.Const(VendorGroup.__coreobjects_type__, "type")),
                ],
            ),
            "vendor": autocomplete.ModelSelect2(
                url="coreobjects-autocomplete",
                forward=[
                    (forward.Const(Vendor.__coreobjects_type__, "type")),
                ],
            ),
        }


class ConnectorVendorInfoInline(admin.StackedInline):
    model = ConnectorVendorInfo
    form = ConnectorVendorInfoForm
    extra = 1
    fields = [
        "vendor_group",
        "vendor",
        "contains_support_document",
        "requires_account_number",
    ]
    ordering = ("-created_date",)


def move_connector_for_manual_invoice_download(
    modeladmin: admin.ModelAdmin, request, queryset: QuerySet
):
    """Update connectors in queryset to manual connectors"""
    connectors = list(queryset.all())
    LOGGER.info(
        f"[tag:MVFMID10] User {request.user.remote_id} requested to move connectors to manual"
        f" for following connectors: {[cr.id for cr in connectors]}"
    )

    created = []

    for connector in connectors:
        LOGGER.info(
            f"[tag:MVFMID20] Connector update requested for connector id : {connector.id}"
        )
        connector.enabled = True
        # keeping it 1 for all the connectors, can be updated from connector change page for each connector
        connector.frequency = 1
        connector.adapter_code = "manual"
        connector.save()
        created.append(connector)

    created = ", ".join(
        [
            f'<a href="{reverse("admin:definitions_connector_change", args=(c.id,))}">{str(c)}</a>'
            for c in created
        ]
    )
    message = f"Successfully moved connectors to manual : {created or None}"
    level = messages.INFO
    modeladmin.message_user(request, message=mark_safe(message), level=level)

    # if the user was on a page with filters set, we want to send the user back to the same page
    redirect_to = request.META.get("HTTP_REFERER") or reverse(
        "admin:definitions_connector_changelist"
    )
    return HttpResponseRedirect(redirect_to)


@admin.register(Connector)
class ConnectorAdmin(BaseAdmin):
    vendor_group = to_link(
        "connector_vendor__vendor_group", short_description="Vendor Group"
    )
    vendor = to_link("connector_vendor__vendor", short_description="Vendor")

    fieldsets = [
        (
            "Quick Links",
            {
                "fields": ("shortcuts",),
            },
        ),
        (
            "Attributes",
            {
                "fields": [f.name for f in Connector._meta.concrete_fields],
            },
        ),
    ]

    search_fields = (
        "id",
        "name",
        "login_url",
        "adapter_code",
    )
    list_display = (
        "name",
        "icon_img",
        "enabled",
        "adapter_code",
        "supported_capabilities",
        "type",
        "vendor_group",
        "vendor",
        "disabled_reason",
        "disabled_reason_text",
        "login_url",
    )
    list_filter = (
        "enabled",
        "type",
        BacklogFilter.new(join_prefix=""),
        "capabilities__type",
        "adapter_code",
    )
    list_display_links = ("name", "icon_img")
    ordering = ("name",)

    @action_short_description("Move for manual invoice download")
    def move_to_manual(self, request, connector_id: Union[str, QuerySet]):
        """
        :param request: Request
        :param connector_id: This can be queryset (if called from django admin list action) or str if called
                       from django `admin/definitions/connector/<connector_id>/` view
        :return:
        """
        queryset = (
            Connector.objects.filter(pk=connector_id)
            if isinstance(connector_id, str)
            else connector_id
        )
        return move_connector_for_manual_invoice_download(self, request, queryset)

    # inlines = [
    #     ConnectorVendorInfoInline,
    # ]
    actions = [move_to_manual]

    def get_queryset(self, request):
        queryset = (
            super()
            .get_queryset(request)
            .select_related(
                "connector_vendor",
                "connector_vendor__vendor_group",
                "connector_vendor__vendor",
            )
            .prefetch_related("capabilities")
        )
        return queryset

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        readonly_fields += ["shortcuts"]
        return readonly_fields

    def get_inline_instances(self, request, obj=None):
        class FileDiscoveryActionInline(admin.TabularInline):
            model = FileDiscoveryAction
            extra = 0
            fields = ["document_type", "action_type", "edi_parser_code"]
            ordering = ("document_type",)

        inlines = []
        if obj and ConnectorType(obj.type) == ConnectorType.VENDOR:
            inlines = [
                ConnectorVendorInfoInline,
                ConnectorCapabilityInline,
                FileDiscoveryActionInline,
            ]

        if obj and ConnectorType(obj.type) == ConnectorType.ACCOUNTING:
            inlines = [ConnectorCapabilityInline, FileDiscoveryActionInline]

        return [inline(self.model, self.admin_site) for inline in inlines]

    @staticmethod
    def shortcuts(obj):
        if not obj or not obj.id:
            return "-"

        jobs_url = f"{reverse('admin:jobconfig_job_changelist')}?connector={obj.id}"
        runs_url = f"{reverse('admin:runs_run_changelist')}?job__connector={obj.id}"

        return format_html(
            f"""
                <div>
                    <span><a href="{jobs_url}">Related Jobs</a></span>
                    &nbsp;&nbsp;|&nbsp;&nbsp;
                    <span><a href="{runs_url}">Related Runs</a></span>
                </div>
            """
        )

    @staticmethod
    def supported_capabilities(obj):
        return ", ".join([ei.type.message for ei in obj.capabilities.all()]) or "-"

    @staticmethod
    @action_short_description("Icon")
    def icon_img(obj: Connector):
        if not obj or not obj.id or not obj.icon:
            return "-"

        return format_html(f'<img src="{obj.icon.url}" width="20px"/>')


# @admin.register(ConnectorVendorInfo)
class ConnectorVendorInfoAdmin(BaseAdmin):
    form = ConnectorVendorInfoForm

    fields = [f.name for f in ConnectorVendorInfo._meta.concrete_fields]
    search_fields = ("connector__adapter_code", "vendor__display_name")
    list_display = (
        "connector_id",
        to_link("connector", short_description="connector"),
        "vendor_group_name",
        "vendor_name",
        "contains_support_document",
        "requires_account_number",
    )
    list_filter = (
        "contains_support_document",
        "requires_account_number",
        "connector",
    )
    ordering = ("-created_date",)

    @classmethod
    def vendor_group_name(cls, obj):
        return (
            f"{obj.vendor_group.remote_id} - {obj.vendor_group.display_name}"
            if obj.vendor_group
            else None
        )

    @classmethod
    def vendor_name(cls, obj):
        return (
            f"{obj.vendor.remote_id} - {obj.vendor.display_name}"
            if obj.vendor
            else None
        )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj:  # editing an existing object
            return readonly_fields + ["connector"]
        return readonly_fields

    def get_autocomplete_fields(self, request):
        return ["connector"]

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        # This is add to remove edit/delete options for foreign keys
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)

        if db_field.name in ("vendor", "vendor_group"):
            formfield.widget.can_delete_related = False
            formfield.widget.can_change_related = False

        return formfield
