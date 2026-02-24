import django_filters
from django.core.exceptions import ValidationError
from django.db.models import Q
from django_filters.rest_framework import BooleanFilter
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from spices.django3 import thread_local
from spices.django3.coreobjects.base import SharedCoreObjectModel
from spices.django3.coreobjects.models import Location, Account, LocationGroup
from spices.django3.coreobjects.views import SharedCoreObjectFilter
from spices.services import ServiceClientError

from apps.adapters import engine
from apps.definitions.models import Connector, ConnectorCapabilityTypes, ConnectorType
from apps.jobconfig import LOGGER
from apps.jobconfig.models import PIQMapping, Job, ConnectorRequest, JobSchedule
from apps.jobconfig.serializers import (
    JobReadSerializer,
    PIQMappingSerializer,
    JobWriteSerializer,
    ConnectorRequestSerializer,
    JobScheduleSerializer,
)
from apps.runs.models import RunStatus, RunCreatedVia
from apps.runs.run_factory import create_run
from apps.utils.base import AccountAuthenticatedApiView
from apps.utils.piq_core import FakeRequest
from integrator.conf import PIQ_API_TOKEN


class JobFilterSet(SharedCoreObjectFilter):
    name = django_filters.CharFilter(method="string_search")
    company_id = django_filters.CharFilter(method="filter_over_company_id")
    enabled = BooleanFilter(field_name="enabled", method="filter_enabled")
    adapter_code = django_filters.CharFilter(method="filter_adapter_code")

    # pylint: disable=no-self-use, unused-argument
    def string_search(self, queryset, name, value):
        if value:
            value = str(value).strip()
            queryset = queryset.filter(connector__name__icontains=value)
        return queryset

    # pylint: disable=no-self-use, unused-argument
    def filter_enabled(self, queryset, name, value):
        filter_qs = Q()
        if value:
            filter_qs &= Q(enabled=value) & Q(connector__enabled=value)
        else:
            filter_qs &= Q(enabled=value) | Q(connector__enabled=value)
        return queryset.filter(filter_qs)

    # pylint: disable=no-self-use, unused-argument
    def filter_over_company_id(self, queryset, name, value):
        if value:
            value = str(value).strip()
            queryset = queryset.filter(companies__remote_id=value)
        return queryset

    # pylint: disable=no-self-use, unused-argument
    def filter_adapter_code(self, queryset, name, value):
        if value:
            value = str(value).strip()
            queryset = queryset.filter(connector__adapter_code=value)
        return queryset

    class Meta:
        model = Job
        fields = [
            "enabled",
            "connector_id",
            "account",
            "location",
            "location_group",
            "name",
            "company_id",
            "connector__adapter_code",
        ]


class JobViewSet(AccountAuthenticatedApiView, viewsets.ModelViewSet):
    serializer_class = JobReadSerializer
    filterset_class = JobFilterSet
    ordering_fields = ("id", "connector_id", "enabled")
    ordering = ("id",)
    allow_staff_access = True

    action_serializers = {
        "create": JobWriteSerializer,
        "partial_update": JobWriteSerializer,
    }

    def get_serializer_class(self):
        if hasattr(self, "action_serializers"):
            return self.action_serializers.get(self.action, self.serializer_class)

        return super().get_serializer_class()

    def get_queryset(self):
        queryset = (
            Job.objects.all()
            .exclude(connector__adapter_code="backlog")
            .select_related("connector", "connector__connector_vendor")
            .prefetch_related("piq_mappings", "connector__capabilities")
        )

        if self.request.user and self.request.user.is_authenticated:
            # TODO: remove "if" condition, this should be mandatory
            # queryset = queryset.filter(account__remote_id__in=self.request.user.user_accounts)
            pass

        # Following fields needs to be removed once the server is updated
        location_group_id = self.request.query_params.get("restaurant_group_id", None)
        location_id = self.request.query_params.get("restaurant_id", None)
        account_ids = self.request.query_params.getlist("restaurant_account_id", None)
        # company_id = self.request.query_params.get('restaurant_company_id', None)

        filter_qs = Q()

        # Following fields needs to be removed once the server is updated
        if location_group_id:
            filter_qs &= Q(location_group__remote_id=location_group_id)

        if location_id:
            filter_qs &= Q(location__remote_id=location_id)

        if account_ids:
            filter_qs &= Q(account__remote_id__in=account_ids)

        queryset = queryset.filter(filter_qs).distinct()
        return queryset

    @staticmethod
    def _preprocess_site_keys(request, is_patch=False):
        if not is_patch:
            if "connector" not in request.data:
                request.data["connector"] = request.data["site"]

        if request.data.get("location_id") is None:
            request.data["location_id"] = request.data.get("restaurant_id")

        if request.data.get("location_group_id") is None:
            request.data["location_group_id"] = request.data.get("restaurant_group_id")

        if request.data.get("account_id") is None:
            request.data["account_id"] = request.data.get("restaurant_account_id")

    def _validate_and_get_account_id(self, request):
        if not request.data["account_id"]:
            return Response(
                data={"account_id": ["This field is required and may not be null"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.data["account_id"] not in self.account_ids:
            raise ServiceClientError(
                http_status_code=status.HTTP_404_NOT_FOUND,
                code="ACCOUNT_NOT_FOUND",
                message="Unknown account",
            )

        account = Account.try_retrieve(
            request=FakeRequest(token=PIQ_API_TOKEN),
            pk=request.data["account_id"],
            cache_locally=True,
        )
        if not account:
            raise ServiceClientError(
                http_status_code=status.HTTP_404_NOT_FOUND,
                code="ACCOUNT_NOT_FOUND",
                message="Unknown account",
            )

        return account

    @staticmethod
    def _validate_whether_job_exists(validated_data: dict, account_id: str):
        LOGGER.info(
            f'[tag:VWJE][aid:{account_id}][un:{validated_data.get("username")}]'
            f'[cid:{validated_data.get("connector")}][lurl:{validated_data.get("login_url")}] '
            f"Validating while creating/updating job for "
        )
        try:
            connector_ = validated_data["connector"]
            login_url = (
                (validated_data["login_url"] or "")
                if connector_.has_configurable_login_url
                else ""
            )
            # Validating whether job exists with the same data
            job = Job.objects.get(
                connector_id=connector_.id,
                username=validated_data["username"],
                login_url=login_url,
            )
            #  if exists, validating account id with the payload account id
            if job.account_id == account_id:
                if "password" in validated_data:
                    # updating the password
                    job.password = validated_data["password"]
                    job.save()
                return Response(
                    JobReadSerializer(job).data, status=status.HTTP_409_CONFLICT
                )
            # job exists, but for different account raise error without job data.
            return Response(status=status.HTTP_409_CONFLICT)

        except Job.DoesNotExist:
            return None

    def create(self, request, *args, **kwargs):
        self._preprocess_site_keys(request)
        account = self._validate_and_get_account_id(request)

        serializer = JobWriteSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        # validating if job exists
        validated_data["connector"] = Connector.objects.get(
            pk=serializer.initial_data["connector"]
        )
        exists_response = self._validate_whether_job_exists(validated_data, account.id)
        if exists_response:
            return exists_response

        validated_data = self._validate_location_data(request, validated_data)

        # pylint: disable=protected-access
        validated_data["account"] = account

        instance = serializer.save()

        created_job = self.get_serializer_class()(instance)
        return Response(created_job.data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _validate_location_data(request, validated_data):
        fake_request = FakeRequest(token=PIQ_API_TOKEN)
        if request.data["location_group_id"]:
            location_group = LocationGroup.try_retrieve(
                request=fake_request,
                pk=request.data["location_group_id"],
                cache_locally=True,
            )
            validated_data["location_group"] = location_group
        if request.data["location_id"]:
            location = Location.try_retrieve(
                request=fake_request, pk=request.data["location_id"], cache_locally=True
            )
            validated_data["location"] = location
        return validated_data

    def partial_update(
        self, request, *args, **kwargs
    ):  # pylint: disable=unused-argument
        instance = self.get_object()

        self._preprocess_site_keys(request, is_patch=True)
        account = self._validate_and_get_account_id(request)

        serializer = self.get_serializer_class()(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        if instance.username != validated_data.get(
            "username", instance.username
        ) or instance.login_url != validated_data.get("login_url", instance.login_url):
            if "username" not in validated_data:
                validated_data["username"] = instance.username
            if "login_url" not in validated_data:
                validated_data["login_url"] = instance.login_url
            validated_data["connector"] = instance.connector
            exists_response = self._validate_whether_job_exists(
                validated_data, account.id
            )
            if exists_response:
                return exists_response

        validated_data = self._validate_location_data(request, validated_data)

        # pylint: disable=protected-access
        validated_data["account"] = account

        serializer.save()

        if getattr(instance, "_prefetched_objects_cache", None):
            instance = self.get_object()
            serializer = self.get_serializer(instance)

        return Response(serializer.data)

    # pylint: disable=unused-argument
    def update(self, request, pk=None):
        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        detail=True,
        methods=["GET"],
        url_path="validate-credentials",
        url_name="validate_credentials",
    )
    def validate_credentials(self, request, pk=None):
        job = self.get_object()
        is_login_success = False
        suppress_invoices = request.query_params.get("suppress_invoices", False)
        run = create_run(
            job,
            ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN,
            RunCreatedVia.CUSTOMER_REQUEST,
            dry_run=True,
            suppress_invoices=suppress_invoices,
        )

        try:
            engine.crawl(run)
        except Exception as ex:  # pylint: disable=broad-except
            LOGGER.error(f"Run: {run} failed with exception: {ex}")

        if run.status == RunStatus.SUCCEEDED.ident:  # pylint: disable=no-member
            is_login_success = True

        return Response({"is_login_success": is_login_success})

    @action(detail=True, methods=["POST"], url_path="run-job", url_name="run")
    def run_job(self, request, pk=None):
        job: Job = self.get_object()
        suppress_invoices = bool(request.data.get("suppress_invoices", False))
        dry_run = str(request.data.get("dry_run")).lower() == "true"
        if not job.connector.enabled:
            raise ServiceClientError(
                http_status_code=status.HTTP_400_BAD_REQUEST,
                code="DISABLED",
                message="Connector is disabled",
            )

        import_payments = bool(request.data.get("import_payments", False))
        if dry_run:
            operation = ConnectorCapabilityTypes.INTERNAL__WEB_LOGIN
        elif ConnectorType(job.connector.type) == ConnectorType.ACCOUNTING:
            if import_payments:
                operation = ConnectorCapabilityTypes.PAYMENT__IMPORT_INFO
            else:
                operation = ConnectorCapabilityTypes.PAYMENT__EXPORT_INFO
        elif ConnectorType(job.connector.type) == ConnectorType.VENDOR:
            operation = ConnectorCapabilityTypes.INVOICE__DOWNLOAD
        else:
            raise ServiceClientError(
                http_status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_OPERATION",
                message="Operation is not allowed",
            )

        is_manual = False  # customer requested runs should not be manual
        if job.connector.is_manual:
            # we can't have non-manual runs of manual-only connectors
            is_manual = True
            current_user = thread_local.get_current_request_user()
            LOGGER.info(
                f"[tag:WJVJRJ10][cid:{job.connector_id}][job:{job.id}] "
                f"Manual run was requested by user {current_user}"
            )

        run = create_run(
            job,
            operation,
            RunCreatedVia.CUSTOMER_REQUEST,
            dry_run=dry_run,
            suppress_invoices=suppress_invoices,
            import_payments=import_payments,
            is_manual=is_manual,
        )
        run.execute_async(on_demand=True)

        # TODO: should return 201
        return Response(
            status=status.HTTP_200_OK,
            data={
                "run": {
                    "id": run.id,
                    "status": run.status,
                    "status_text": RunStatus(
                        run.status
                    ).message,  # pylint: disable=no-value-for-parameter
                }
            },
        )


class JobPIQMappingViewSet(AccountAuthenticatedApiView, viewsets.ModelViewSet):
    serializer_class = PIQMappingSerializer
    filterset_fields = ("piq_data__remote_id",)
    ordering_fields = ("id", "piq_data__remote_id", "mapping_data")
    ordering = ("id",)
    acl_field = "job__account"

    def get_queryset(self):
        queryset = PIQMapping.objects.filter(
            job=self.kwargs["job_id"]
        ).prefetch_related("job")

        location_id = self.request.query_params.get("location_id", None)
        piq_restaurant_id = self.request.query_params.get("piq_restaurant_id", None)
        name = self.request.query_params.get("name", None)

        filter_qs = Q()

        if piq_restaurant_id:
            filter_qs &= Q(piq_data__remote_id=piq_restaurant_id)

        if location_id:
            filter_qs &= Q(piq_data__remote_id=location_id)

        if name:
            filter_qs &= Q(mapping_data__iexact=name)

        queryset = queryset.filter(filter_qs)
        return queryset

    @classmethod
    def get_piq_data(cls, request):
        mapping_type = (
            "r" if request.data.get("piq_restaurant_id") is not None else None
        )

        if not mapping_type:
            mapping_type = (
                request.data["type"] if request.data.get("type") is not None else None
            )

        model_cls = SharedCoreObjectModel.model_for_type(mapping_type)
        if model_cls:
            mock_request = FakeRequest(token=PIQ_API_TOKEN)
            return model_cls.try_retrieve(
                request=mock_request, pk=request.data["piq_data_id"], cache_locally=True
            )
        return None

    def create(self, request, *args, **kwargs):
        request.data["job"] = kwargs["job_id"]

        # validate that user has access to the job
        get_object_or_404(
            Job.objects.filter(account__remote_id__in=self.account_ids),
            pk=kwargs["job_id"],
        )

        if request.data.get("mapping_data") is None:
            request.data["mapping_data"] = (
                request.data["name"] if request.data.get("name") is not None else None
            )

        serializer = PIQMappingSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        if request.data.get("piq_data_id") is None:
            request.data["piq_data_id"] = (
                request.data["piq_restaurant_id"]
                if request.data.get("piq_restaurant_id") is not None
                else None
            )

        if not request.data["piq_data_id"]:
            return Response(
                data={"piq_data_id": ["This field is required and may not be null"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        piq_data = self.get_piq_data(request)

        if not piq_data:
            error_response = {
                "error": f'piq_data_id: {request.data["piq_data_id"]} not found'
            }
            return Response(error_response, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(piq_data, Response):
            return piq_data

        instance = PIQMapping.objects.filter(
            job=request.data["job"],
            piq_data__remote_id=request.data["piq_data_id"],
            piq_data__type=piq_data.type,
            mapping_data__iexact=request.data["mapping_data"],
        )
        if instance:
            error_response = {
                "error": f'piq_data_id: {request.data["piq_data_id"]}, mapping_data: {request.data["mapping_data"]}'
                f" already Exists"
            }
            return Response(error_response, status=status.HTTP_409_CONFLICT)

        serializer._validated_data[  # pylint: disable=protected-access
            "piq_data"
        ] = piq_data
        instance = serializer.save()
        created_piq_mapping = PIQMappingSerializer(instance)
        return Response(created_piq_mapping.data, status=status.HTTP_201_CREATED)

    # pylint: disable=unused-argument
    def partial_update(self, request, *args, pk=None, **kwargs):
        request.data["job"] = kwargs["job_id"]
        queryset = PIQMapping.objects.all().prefetch_related("job")

        # validate that the user has access to the job
        instance = get_object_or_404(self.filter_queryset(queryset), pk=pk)

        if request.data.get("mapping_data") is None:
            request.data["mapping_data"] = (
                request.data["name"] if request.data.get("name") is not None else None
            )

        serializer = self.get_serializer_class()(
            instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)

        if request.data.get("piq_data_id") is None:
            request.data["piq_data_id"] = (
                request.data["piq_restaurant_id"]
                if request.data.get("piq_restaurant_id") is not None
                else None
            )

        if not request.data["piq_data_id"]:
            return Response(
                data={"piq_data_id": ["This field is required and may not be null"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        piq_data = self.get_piq_data(request)

        if not piq_data:
            error_response = {
                "error": f'piq_data_id: {request.data["piq_data_id"]} not found'
            }
            return Response(error_response, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(piq_data, Response):
            return piq_data

        instance = PIQMapping.objects.filter(
            job=request.data["job"],
            piq_data__remote_id=request.data["piq_data_id"],
            piq_data__type=piq_data.type,
            mapping_data__iexact=request.data["mapping_data"],
        )
        if instance and instance[0].id != pk:
            error_response = {
                "error": f'piq_data_id: {request.data["piq_data_id"]}, mapping_data: {request.data["mapping_data"]}'
                f" already Exists"
            }
            return Response(error_response, status=status.HTTP_409_CONFLICT)

        serializer._validated_data[  # pylint: disable=protected-access
            "piq_data"
        ] = piq_data
        serializer.save()

        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response(serializer.data)


class ConnectorRequestFilterSet(SharedCoreObjectFilter):
    class Meta:
        model = ConnectorRequest
        fields = ["account"]


class ConnectorRequestViewSet(AccountAuthenticatedApiView, viewsets.ModelViewSet):
    serializer_class = ConnectorRequestSerializer
    filterset_class = ConnectorRequestFilterSet
    ordering_fields = (
        "name",
        "created_date",
    )
    ordering = ("-created_date",)
    queryset = ConnectorRequest.objects.all()  # auto-excludes deleted

    # def get_serializer_class(self):
    #     if self.action in ('create', 'update', 'partial_update'):
    #         return ConnectorRequestWriteSerializer
    #     return self.serializer_class

    def _validate_and_get_account_id(self, request):
        if not request.data["account_id"]:
            return Response(
                data={"account_id": ["This field is required and may not be null"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if request.data["account_id"] not in self.account_ids:
            raise ServiceClientError(
                http_status_code=status.HTTP_404_NOT_FOUND,
                code="ACCOUNT_NOT_FOUND",
                message="Unknown account",
            )

        account = Account.try_retrieve(
            request=FakeRequest(token=PIQ_API_TOKEN),
            pk=request.data["account_id"],
            cache_locally=True,
        )
        if not account:
            raise ServiceClientError(
                http_status_code=status.HTTP_404_NOT_FOUND,
                code="ACCOUNT_NOT_FOUND",
                message="Unknown account",
            )

        return account

    def perform_create(self, serializer):
        account = self._validate_and_get_account_id(self.request)
        serializer._validated_data[  # pylint: disable=protected-access
            "account"
        ] = account
        return super().perform_create(serializer)


class JobScheduleViewSet(AccountAuthenticatedApiView, viewsets.ModelViewSet):
    serializer_class = JobScheduleSerializer
    queryset = JobSchedule.objects.all()
    allow_staff_access = True
    acl_field = "job__account"

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as ex:
            raise ServiceClientError(
                http_status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_REQUEST",
                message=f"Invalid Request. Error: {ex.args[0]}",
            )

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True

        try:
            return super().update(
                request, *args, **kwargs
            )  # Note: we are calling super.update, NOT partial_update
        except ValidationError as ex:
            raise ServiceClientError(
                http_status_code=status.HTTP_400_BAD_REQUEST,
                code="INVALID_REQUEST",
                message=f"Invalid Request. Error: {ex.args[0]}",
            )
