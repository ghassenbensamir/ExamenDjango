from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from web3 import Web3
from django.conf import settings
import json
import logging

from .models import Transaction, ContractEvent
from .serializers import (
    TransactionSerializer,
    ContractEventSerializer, 
    SubmitTransactionInputSerializer, 
    TriggerEventInputSerializer
)

logger = logging.getLogger(__name__)

# --- Database Model Views --- 

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows transactions to be viewed."""
    queryset = Transaction.objects.all().order_by("-block_number")
    serializer_class = TransactionSerializer
    lookup_field = "transaction_hash" # Use tx hash for lookup instead of pk
    permission_classes = [permissions.AllowAny] # Or adjust as needed

class ContractEventViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint that allows contract events to be viewed."""
    queryset = ContractEvent.objects.all().order_by("-block_timestamp", "-log_index")
    serializer_class = ContractEventSerializer
    permission_classes = [permissions.AllowAny] # Or adjust as needed

    # Optional: Add filtering capabilities, e.g., filter by transaction hash
    # filter_backends = [DjangoFilterBackend]
    # filterset_fields = ["transaction__transaction_hash", "event_name", "contract_address"]

# --- Web3 Interaction Views (Remain largely the same as they trigger contract functions) --- 

# Configure Web3 connection
GANACHE_URL = getattr(settings, "GANACHE_URL", "http://127.0.0.1:7545")
w3 = Web3(Web3.HTTPProvider(GANACHE_URL))

# Load Contract ABI and Address
CONTRACT_ADDRESS = getattr(settings, "TRANSACTION_CONTRACT_ADDRESS", None) 
CONTRACT_ABI_PATH = getattr(settings, "TRANSACTION_CONTRACT_ABI_PATH", None) 

contract_instance = None
if not w3.is_connected():
    logger.error(f"Failed to connect to Web3 provider at {GANACHE_URL}")
elif CONTRACT_ADDRESS and CONTRACT_ABI_PATH:
    try:
        logger.info(f"Loading ABI from: {CONTRACT_ABI_PATH}")
        with open(CONTRACT_ABI_PATH, "r") as abi_file:
            abi_data = json.load(abi_file)
            contract_abi = abi_data if isinstance(abi_data, list) else abi_data.get("abi")
            if not contract_abi:
                 raise ValueError("ABI array not found in JSON file.")
        contract_instance = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)
        logger.info(f"Contract instance created for address: {CONTRACT_ADDRESS}")
    except FileNotFoundError:
        logger.error(f"ABI file not found at {CONTRACT_ABI_PATH}")
        contract_instance = None
    except Exception as e:
        logger.error(f"Could not load contract ABI/Address for {CONTRACT_ADDRESS}: {e}")
        contract_instance = None
else:
    logger.warning("TRANSACTION_CONTRACT_ADDRESS or TRANSACTION_CONTRACT_ABI_PATH not set in Django settings.")

class SubmitTransactionView(APIView):
    """Endpoint to invoke the submitTransaction method on the TransactionContract."""
    permission_classes = [permissions.AllowAny] # Adjust as needed

    def post(self, request, *args, **kwargs):
        if not contract_instance:
            return Response({"error": "Contract not initialized. Check server configuration."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = SubmitTransactionInputSerializer(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            to_address = validated_data["to_address"]
            amount = validated_data["amount"]
            tx_hash_param = validated_data["tx_hash_param"]

            try:
                # Use default Ganache account - INSECURE FOR PRODUCTION
                sender_account = w3.eth.accounts[0]
                w3.eth.default_account = sender_account
                logger.info(f"Attempting to call submitTransaction from account: {sender_account}")

                tx_hash = contract_instance.functions.submitTransaction(
                    Web3.to_checksum_address(to_address),
                    int(amount),
                    tx_hash_param
                ).transact()
                
                logger.info(f"submitTransaction called. Transaction hash: {tx_hash.hex()}")
                return Response({
                    "message": "Transaction submitted successfully via contract",
                    "transaction_hash": tx_hash.hex()
                }, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(f"Failed to send transaction via submitTransaction: {e}", exc_info=True)
                return Response({"error": f"Failed to send transaction: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TriggerContractEventView(APIView):
    """Endpoint to invoke the triggerEvent method on the TransactionContract."""
    permission_classes = [permissions.AllowAny] # Adjust as needed

    def post(self, request, *args, **kwargs):
        if not contract_instance:
            return Response({"error": "Contract not initialized. Check server configuration."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        serializer = TriggerEventInputSerializer(data=request.data)
        if serializer.is_valid():
            message = serializer.validated_data["message"]

            try:
                # Use default Ganache account - INSECURE FOR PRODUCTION
                sender_account = w3.eth.accounts[0]
                w3.eth.default_account = sender_account
                logger.info(f"Attempting to call triggerEvent from account: {sender_account}")

                tx_hash = contract_instance.functions.triggerEvent(message).transact()
                
                logger.info(f"triggerEvent called. Transaction hash: {tx_hash.hex()}")
                return Response({
                    "message": "Contract event triggered successfully",
                    "transaction_hash": tx_hash.hex()
                }, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(f"Failed to send transaction via triggerEvent: {e}", exc_info=True)
                return Response({"error": f"Failed to trigger event: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

