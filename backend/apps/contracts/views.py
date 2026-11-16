from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common import blob_store

from . import services
from .models import Contract, ContractClause, ContractQuery
from .permissions import IsAdminOrReadOnlyDelete
from .serializers import (
    AskQuestionSerializer,
    ContractClauseSerializer,
    ContractQuerySerializer,
    ContractSerializer,
    ContractUploadSerializer,
)

STUB_BLOB_CONTAINER = "contracts"


class ContractViewSet(viewsets.ModelViewSet):
    """
    Contracts are a shared resource for all legal_reviewer/admin users
    (queryset is not scoped per-uploader - any reviewer/admin can see and
    query any contract). Only `admin` may delete (see IsAdminOrReadOnlyDelete).
    """
    serializer_class = ContractSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnlyDelete]
    queryset = Contract.objects.select_related("uploaded_by").prefetch_related("clauses", "chunks")

    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user)

    @action(detail=False, methods=["post"], url_path="upload")
    def upload(self, request):
        serializer = ContractUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        uploaded_file = data.pop("file")

        blob_path = blob_store.upload_document(uploaded_file, STUB_BLOB_CONTAINER, uploaded_file.name)

        contract = Contract.objects.create(
            uploaded_by=request.user,
            blob_path=blob_path,
            status=Contract.Status.UPLOADED,
            **data,
        )
        return Response(ContractSerializer(contract).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="process")
    def process(self, request, pk=None):
        contract = self.get_object()
        try:
            services.process_contract(contract)
        except Exception as exc:
            return Response(
                {"detail": f"Processing failed: {exc}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        contract.refresh_from_db()
        return Response(ContractSerializer(contract).data)

    @action(detail=True, methods=["get"], url_path="clauses")
    def clauses(self, request, pk=None):
        contract = self.get_object()
        clauses = contract.clauses.all()
        return Response(ContractClauseSerializer(clauses, many=True).data)


class ContractClauseViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ContractClauseSerializer
    permission_classes = [IsAuthenticated]
    queryset = ContractClause.objects.select_related("contract")

    def get_queryset(self):
        qs = super().get_queryset()
        contract_id = self.request.query_params.get("contract")
        if contract_id:
            qs = qs.filter(contract_id=contract_id)
        return qs


class ContractQueryViewSet(viewsets.ModelViewSet):
    """
    History is scoped at the queryset level: legal_reviewer sees only the
    questions they personally asked; admin sees every query across all users.
    """
    serializer_class = ContractQuerySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = ContractQuery.objects.select_related("asked_by", "contract")
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return qs
        return qs.filter(asked_by=user)

    def create(self, request, *args, **kwargs):
        serializer = AskQuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        contract = None
        contract_id = data.get("contract_id")
        if contract_id:
            contract = get_object_or_404(Contract, pk=contract_id)

        query = services.ask_question(
            user=request.user,
            question_text=data["question_text"],
            contract=contract,
            top_k=data.get("top_k", 5),
        )
        return Response(ContractQuerySerializer(query).data, status=status.HTTP_201_CREATED)
