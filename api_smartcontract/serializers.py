# /home/ubuntu/web3_project/api/serializers.py
from rest_framework import serializers
from .models import Transaction, ContractEvent
from .validators import validate_blockchain_address, validate_transaction_hash, validate_block_number

class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for the Transaction model."""
    # Expose the related events using the related_name defined in the ContractEvent model
    # This will show a list of primary keys by default, or use nested serializer for full details
    events = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # Or for nested details (can be verbose):
    # events = ContractEventSerializer(many=True, read_only=True) 

    class Meta:
        model = Transaction
        fields = (
            "transaction_hash", 
            "block_number", 
            "created_at",
            "events" # Include the related events field
        )
        read_only_fields = ("created_at", "events")

class ContractEventSerializer(serializers.ModelSerializer):
    """Serializer for the ContractEvent model, linked to a Transaction."""
    # Display the transaction hash (primary key) for the related transaction
    transaction = serializers.PrimaryKeyRelatedField(read_only=True)
    # Or display more transaction details using nested serializer:
    # transaction = TransactionSerializer(read_only=True)

    # Keep validators for fields that might be manually set (though unlikely here)
    contract_address = serializers.CharField(validators=[validate_blockchain_address])
    event_from_address = serializers.CharField(validators=[validate_blockchain_address], required=False, allow_null=True)
    event_to_address = serializers.CharField(validators=[validate_blockchain_address], required=False, allow_null=True)
    event_sender_address = serializers.CharField(validators=[validate_blockchain_address], required=False, allow_null=True)

    class Meta:
        model = ContractEvent
        fields = (
            "id",
            "transaction", # Link to the transaction
            "log_index",
            "event_name",
            "contract_address",
            "block_timestamp",
            "is_fraudulent",
            "data", # Raw decoded args JSON
            # Specific fields for easier access
            "event_from_address",
            "event_to_address",
            "event_amount",
            "event_tx_hash_param",
            "event_sender_address",
            "event_message",
            "event_onchain_timestamp",
        )
        # Most fields are derived from the blockchain event and set during creation
        read_only_fields = (
            "id", "transaction", "log_index", "event_name", "contract_address", 
            "block_timestamp", "is_fraudulent", "data",
            "event_from_address", "event_to_address", "event_amount",
            "event_tx_hash_param", "event_sender_address", "event_message",
            "event_onchain_timestamp",
        )

# --- Input Serializers for Contract Interaction (Remain the same) --- 

class SubmitTransactionInputSerializer(serializers.Serializer):
    """Serializer for input to the submitTransaction contract function."""
    to_address = serializers.CharField(validators=[validate_blockchain_address], label="Receiver Address")
    amount = serializers.DecimalField(max_digits=78, decimal_places=0, label="Amount (Wei)")
    tx_hash_param = serializers.CharField(max_length=256, label="Transaction Hash Parameter (String)")

class TriggerEventInputSerializer(serializers.Serializer):
    """Serializer for input to the triggerEvent contract function."""
    message = serializers.CharField(max_length=1024, label="Message String")

