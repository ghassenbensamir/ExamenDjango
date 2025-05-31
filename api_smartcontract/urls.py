from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContractEventViewSet,SubmitTransactionView, TriggerContractEventView


router = DefaultRouter()
# Register the read-only endpoint for viewing stored events
router.register(r'events', ContractEventViewSet, basename='contractevent')

# Define specific paths for contract interaction views
urlpatterns = [
    # Include the router URLs for listing/retrieving events (/api/events/)
    path('', include(router.urls)),
    # Endpoint to call the submitTransaction function
    path('contract/submit/', SubmitTransactionView.as_view(), name='contract-submit-transaction'),
    # Endpoint to call the triggerEvent function
    path('contract/trigger/', TriggerContractEventView.as_view(), name='contract-trigger-event'),
]