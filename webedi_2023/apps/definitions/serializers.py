from rest_framework import serializers
from spices.django3.coreobjects.serializer import SharedCoreObjSerializer

from apps.definitions.models import Connector, ConnectorVendorInfo, ConnectorCapability


class ConnectorVendorInfoSerializer(serializers.ModelSerializer):
    vendor = SharedCoreObjSerializer(allow_null=True, read_only=True)
    vendor_group = SharedCoreObjSerializer(allow_null=True, read_only=True)
    vendor_id = serializers.SerializerMethodField()
    vendor_group_id = serializers.SerializerMethodField()

    @classmethod
    def get_vendor_id(cls, obj):
        return int(obj.vendor.remote_id) if obj.vendor else None

    @classmethod
    def get_vendor_group_id(cls, obj):
        return int(obj.vendor_group.remote_id) if obj.vendor_group else None

    class Meta:
        model = ConnectorVendorInfo
        fields = (
            "vendor_group",
            "vendor",
            "vendor_id",
            "vendor_group_id",
            "contains_support_document",
            "requires_account_number",
        )
        read_only_fields = (
            "vendor_group",
            "vendor",
            "vendor_id",
            "vendor_group_id",
            "contains_support_document",
            "requires_account_number",
        )


class ConnectorCapabilitySerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    supported_file_format = serializers.SerializerMethodField()

    @classmethod
    def get_type(cls, obj):
        return str(obj.type) if obj.type else None

    @classmethod
    def get_supported_file_format(cls, obj):
        return str(obj.supported_file_format) if obj.supported_file_format else None

    class Meta:
        model = ConnectorCapability
        fields = ("type", "supported_file_format")
        read_only_fields = ("id", "type", "supported_file_format")


class ConnectorSerializer(serializers.ModelSerializer):
    connector_vendor_info = ConnectorVendorInfoSerializer(
        allow_null=True,
        read_only=True,
        source="connector_vendor",
    )
    capabilities = ConnectorCapabilitySerializer(
        many=True,
        read_only=True,
    )
    adapter_code = serializers.SerializerMethodField("get_adapter_code")
    icon_url = serializers.SerializerMethodField("get_icon_url")

    @classmethod
    def get_adapter_code(cls, obj):
        return obj.adapter_code

    @classmethod
    def get_icon_url(cls, obj):
        return obj.icon.url if obj.icon else None

    class Meta:
        model = Connector
        fields = (
            "id",
            "adapter_code",
            "name",
            "login_url",
            "registration_url",
            "enabled",
            "type",
            "icon_url",
            "connector_vendor_info",
            "capabilities",
        )
        read_only_fields = (
            "id",
            "adapter_code",
            "name",
            "login_url",
            "registration_url",
            "enabled",
            "type",
            "icon_url",
            "connector_vendor_info",
            "capabilities",
        )
