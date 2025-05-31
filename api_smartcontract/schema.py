# /home/ubuntu/web3_project/api/schema.py
import graphene
from graphene_django import DjangoObjectType
from .models import Transaction, ContractEvent # Import both models
from .serializers import SubmitTransactionInputSerializer, TriggerEventInputSerializer # Input serializers
from .views import contract_instance, w3 # Reuse contract instance and web3 connection
from web3 import Web3
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# --- Object Types --- 

# Forward declaration for circular dependency (Transaction <-> ContractEvent)
class ContractEventType(graphene.ObjectType):
    pass

class TransactionType(DjangoObjectType):
    class Meta:
        model = Transaction
        fields = (
            "transaction_hash", 
            "block_number", 
            "created_at",
            "events" # Expose related events
        )
    
    # Custom resolver for events to use the correct type
    events = graphene.List(lambda: ContractEventType) # Use lambda for forward reference

    def resolve_events(self, info):
        # Access the related events via the ForeignKey relationship
        return self.events.all()

class ContractEventType(DjangoObjectType):
    # Expose specific event fields directly
    event_from_address = graphene.String()
    event_to_address = graphene.String()
    event_amount = graphene.Decimal()
    event_tx_hash_param = graphene.String()
    event_sender_address = graphene.String()
    event_message = graphene.String()
    event_onchain_timestamp = graphene.BigInt()

    class Meta:
        model = ContractEvent
        fields = (
            "id",
            "transaction", # Expose the related transaction
            "log_index",
            "event_name",
            "contract_address",
            "block_timestamp",
            "is_fraudulent",
            "data", # Raw JSON data
            # Specific fields added above
            "event_from_address",
            "event_to_address",
            "event_amount",
            "event_tx_hash_param",
            "event_sender_address",
            "event_message",
            "event_onchain_timestamp",
        )
    
    # Custom resolver for transaction to use the correct type
    transaction = graphene.Field(TransactionType)

    def resolve_transaction(self, info):
        # Access the related transaction via the ForeignKey
        return self.transaction

# --- Query --- 

class Query(graphene.ObjectType):
    all_transactions = graphene.List(TransactionType)
    transaction_by_hash = graphene.Field(TransactionType, tx_hash=graphene.String(required=True))

    all_contract_events = graphene.List(ContractEventType)
    events_by_transaction = graphene.List(ContractEventType, tx_hash=graphene.String(required=True))
    event_by_id = graphene.Field(ContractEventType, id=graphene.ID(required=True))

    def resolve_all_transactions(root, info):
        return Transaction.objects.all()

    def resolve_transaction_by_hash(root, info, tx_hash):
        try:
            # Use transaction_hash as the primary key lookup
            return Transaction.objects.get(pk=tx_hash)
        except Transaction.DoesNotExist:
            return None

    def resolve_all_contract_events(root, info):
        return ContractEvent.objects.all()

    def resolve_events_by_transaction(root, info, tx_hash):
        # Filter events based on the transaction hash (foreign key)
        return ContractEvent.objects.filter(transaction__transaction_hash=tx_hash)

    def resolve_event_by_id(root, info, id):
        try:
            return ContractEvent.objects.get(pk=id)
        except ContractEvent.DoesNotExist:
            return None

# --- Mutations (Remain the same as they interact with the contract directly) --- 

# Input Object Type for submitTransaction function
class SubmitTransactionInput(graphene.InputObjectType):
    to_address = graphene.String(required=True)
    amount = graphene.Decimal(required=True) # Amount in Wei
    tx_hash_param = graphene.String(required=True)

# Input Object Type for triggerEvent function
class TriggerEventInput(graphene.InputObjectType):
    message = graphene.String(required=True)

class SubmitTransactionMutation(graphene.Mutation):
    class Arguments:
        input = SubmitTransactionInput(required=True)

    success = graphene.Boolean()
    transaction_hash = graphene.String()
    error = graphene.String()

    @staticmethod
    def mutate(root, info, input):
        logger.info(f"Received GraphQL mutation for submitTransaction: {input}")
        if not contract_instance:
            return SubmitTransactionMutation(success=False, error="Contract not initialized on server.")
        try:
            sender_account = w3.eth.accounts[0]
            w3.eth.default_account = sender_account
            logger.warning(f"Executing submitTransaction from hardcoded account: {sender_account}")
            tx_hash = contract_instance.functions.submitTransaction(
                Web3.to_checksum_address(input.to_address),
                int(input.amount),
                input.tx_hash_param
            ).transact()
            logger.info(f"GraphQL submitTransaction successful. Tx hash: {tx_hash.hex()}")
            return SubmitTransactionMutation(success=True, transaction_hash=tx_hash.hex())
        except Exception as e:
            logger.error(f"GraphQL submitTransaction mutation failed: {e}", exc_info=True)
            return SubmitTransactionMutation(success=False, error=f"Transaction submission error: {str(e)}")

class TriggerEventMutation(graphene.Mutation):
    class Arguments:
        input = TriggerEventInput(required=True)

    success = graphene.Boolean()
    transaction_hash = graphene.String()
    error = graphene.String()

    @staticmethod
    def mutate(root, info, input):
        logger.info(f"Received GraphQL mutation for triggerEvent: {input}")
        if not contract_instance:
            return TriggerEventMutation(success=False, error="Contract not initialized on server.")
        try:
            sender_account = w3.eth.accounts[0]
            w3.eth.default_account = sender_account
            logger.warning(f"Executing triggerEvent from hardcoded account: {sender_account}")
            tx_hash = contract_instance.functions.triggerEvent(input.message).transact()
            logger.info(f"GraphQL triggerEvent successful. Tx hash: {tx_hash.hex()}")
            return TriggerEventMutation(success=True, transaction_hash=tx_hash.hex())
        except Exception as e:
            logger.error(f"GraphQL triggerEvent mutation failed: {e}", exc_info=True)
            return TriggerEventMutation(success=False, error=f"Event trigger error: {str(e)}")

class Mutation(graphene.ObjectType):
    submit_contract_transaction = SubmitTransactionMutation.Field()
    trigger_contract_event = TriggerEventMutation.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)

