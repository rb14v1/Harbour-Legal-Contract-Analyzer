from rest_framework.routers import DefaultRouter

from .views import ContractClauseViewSet, ContractQueryViewSet, ContractViewSet

router = DefaultRouter()
router.register("contracts", ContractViewSet, basename="contract")
router.register("clauses", ContractClauseViewSet, basename="contract-clause")
router.register("queries", ContractQueryViewSet, basename="contract-query")

urlpatterns = router.urls
