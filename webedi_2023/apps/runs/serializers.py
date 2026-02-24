from collections import defaultdict

import pytz
from rest_framework import serializers

from apps.definitions.serializers import ConnectorSerializer
from apps.jobconfig.serializers import JobReadSerializer
from apps.runs.models import Run, RunStatus, DiscoveredFile
from spices.django3.issues.serializers import IssueSerializer


class SimpleRunSerializer(serializers.ModelSerializer):
    """
    Run Serializer that does NOT contain parent references
    """

    status_text = serializers.SerializerMethodField("get_status_text")
    execution_start_ts = serializers.DateTimeField(default_timezone=pytz.utc)
    execution_end_ts = serializers.DateTimeField(default_timezone=pytz.utc)
    failure_issue = IssueSerializer()
    action = serializers.SerializerMethodField()

    @classmethod
    def get_action(cls, obj):
        return str(obj.action)

    @classmethod
    def get_status_text(cls, obj):
        return RunStatus(obj.status).message  # pylint: disable=no-value-for-parameter

    class Meta:
        model = Run
        fields = (
            "id",
            "status",
            "status_text",
            "dry_run",
            "request_parameters",
            "failure_issue",
            "execution_start_ts",
            "execution_end_ts",
            "action",
        )
        read_only_fields = fields


class RunSerializer(SimpleRunSerializer):
    job = JobReadSerializer()

    # dict containing discovered files, grouped by customer account number
    grouped_discovered_files = serializers.SerializerMethodField()

    @classmethod
    def get_grouped_discovered_files(cls, obj):
        discovered_files = obj.discovered_files.all()
        discovered_files = [
            df for df in discovered_files if (df.url or df.original_file)
        ]

        grouped = defaultdict(list)
        for df in discovered_files:  # type: DiscoveredFile
            customer_number = (
                df.document_properties.get("customer_number")
                if df.document_properties
                else ""
            )

            grouped[customer_number].append(df)

        return {
            k: SimpleDiscoveredFileSerializer(v, many=True).data
            for k, v in grouped.items()
        }

    class Meta:
        model = SimpleRunSerializer.Meta.model
        fields = SimpleRunSerializer.Meta.fields + ("job", "grouped_discovered_files")
        read_only_fields = fields


class SimpleDiscoveredFileSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    @classmethod
    def get_url(cls, obj: DiscoveredFile):
        if obj.original_file:
            return obj.original_file.url

        return obj.url

    class Meta:
        model = DiscoveredFile
        fields = (
            "id",
            "url",
            "extracted_text_hash",
            "original_filename",
            "original_download_url",
            "file_format",
            "document_type",
            "document_properties",
            "downloaded_at",
            "downloaded_successfully",
            "content_hash",
            "piq_container_id",
            "piq_upload_id",
        )
        read_only_fields = fields


class DiscoveredFileSerializer(SimpleDiscoveredFileSerializer):
    connector = ConnectorSerializer()
    job_id = serializers.SerializerMethodField()

    @classmethod
    def get_job_id(cls, obj):
        return obj.run.job.id

    class Meta:
        model = SimpleDiscoveredFileSerializer.Meta.model
        fields = list(SimpleDiscoveredFileSerializer.Meta.fields)
        fields.extend(
            [
                "run_id",
                "job_id",
                "connector",
            ]
        )
        read_only_fields = fields
