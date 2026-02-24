from copy import copy

from rest_framework import serializers, validators
from spices.django3.coreobjects.models import Company
from spices.django3.coreobjects.serializer import (
    SharedCoreObjSerializer,
    SharedCoreObjectRemoteIdField,
)
from spices.django3.serializer_utils import WriteOnceMixin

from apps.definitions.serializers import ConnectorSerializer
from apps.jobconfig.models import (
    PIQMapping,
    Job,
    FileDiscoveryAction,
    ConnectorRequest,
    JobSchedule,
)


class PIQMappingSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()

    piq_data = SharedCoreObjSerializer(allow_null=False, read_only=True)
    piq_restaurant_id = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    @classmethod
    def get_name(cls, obj):
        return obj.mapping_data if hasattr(obj, "mapping_data") else None

    @classmethod
    def get_piq_restaurant_id(cls, obj):
        if hasattr(obj, "piq_data"):
            return (
                int(obj.piq_data.remote_id)
                if obj.piq_data and obj.piq_data.type == "r"
                else None
            )

        return None

    class Meta:
        model = PIQMapping
        fields = (
            "id",
            "piq_data",
            "piq_restaurant_id",
            "name",
            "mapping_data",
            "mapped_to",
            "job",
        )


class FileDiscoveryActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileDiscoveryAction
        fields = ("document_type", "action_type")


class JobScheduleSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()

    class Meta:
        model = JobSchedule
        fields = (
            "id",
            "job",
            "frequency",
            "week_of_month",
            "day_of_week",
            "date_of_month",
        )


class JobWriteSerializer(serializers.ModelSerializer):
    id = serializers.ReadOnlyField()

    account = SharedCoreObjSerializer(allow_null=False, read_only=True)
    location = SharedCoreObjSerializer(allow_null=False, read_only=True)
    location_group = SharedCoreObjSerializer(allow_null=False, read_only=True)

    file_discovery_action = FileDiscoveryActionSerializer(
        required=False, allow_null=True
    )
    companies = SharedCoreObjectRemoteIdField(
        scom_cls=Company, allow_null=False, required=False, many=True
    )

    def run_validators(self, value):
        for validator in copy(self.validators):
            if isinstance(validator, validators.UniqueTogetherValidator):
                self.validators.remove(validator)
        super(JobWriteSerializer, self).run_validators(value)

    def create(self, validated_data):
        file_discovery_action_dict = validated_data.pop("file_discovery_action", None)
        company_list = validated_data.pop("companies", None)

        job = super().create(validated_data)

        if file_discovery_action_dict:
            file_discovery_action_dict["job"] = job
            FileDiscoveryActionSerializer(context=self.context).create(
                file_discovery_action_dict
            )

        # If companies(remote_id of companies) exists in payload, updating the companies for the job.
        if company_list:
            company_list = Company.objects.filter(id__in=company_list)
            job.companies.set(company_list)
            job.save()

        return job

    class Meta:
        model = Job
        fields = (
            "id",
            "connector",
            "username",
            "password",
            "enabled",
            "account",
            "location_group",
            "location",
            "companies",
            "file_discovery_action",
            "login_url",
        )
        read_only_fields = ("connector",)


class JobReadSerializer(serializers.ModelSerializer):
    connector = ConnectorSerializer()
    piq_mappings = PIQMappingSerializer(many=True, read_only=True)
    schedules = JobScheduleSerializer(many=True, read_only=True)

    enabled = serializers.SerializerMethodField("is_enabled")
    account = SharedCoreObjSerializer(allow_null=False, read_only=True)
    location = SharedCoreObjSerializer(allow_null=False, read_only=True)
    location_group = SharedCoreObjSerializer(allow_null=False, read_only=True)
    last_run = serializers.SerializerMethodField()

    @classmethod
    def get_last_run(cls, obj):
        if not obj.last_run:
            return None

        from apps.runs.serializers import (  # pylint: disable=import-outside-toplevel,cyclic-import
            SimpleRunSerializer,
        )

        return SimpleRunSerializer(instance=obj.last_run).data

    @classmethod
    def is_enabled(cls, obj):
        return obj.enabled and obj.connector.enabled

    class Meta:
        model = Job

        # TODO: Adding last_run here causes the N+1 query problem !
        # Still going with it because the number of jobs returned are going to be low, and there's no
        # easy alternative (except a complicated query as described here: https://stackoverflow.com/a/49944361)
        fields = (
            "id",
            "connector",
            "login_url",
            "username",
            "enabled",
            "last_run",
            "account",
            "location_group",
            "location",
            "companies",
            "piq_mappings",
            "schedules",
        )
        read_only_fields = fields


class ConnectorRequestSerializer(WriteOnceMixin, serializers.ModelSerializer):
    id = serializers.ReadOnlyField()
    account = SharedCoreObjSerializer(allow_null=False, read_only=True)

    class Meta:
        model = ConnectorRequest
        fields = ("id", "account", "type", "name", "login_url", "username", "password")
        read_only_fields = (
            "id",
            "account",
        )
        write_once_fields = ("account", "type")
        extra_kwargs = {"password": {"write_only": True}, "type": {"write_only": True}}
