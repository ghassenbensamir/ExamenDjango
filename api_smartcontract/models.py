from django.db import models

# Create your models here.
from django.utils.translation import gettext_lazy as _
from .validators import validate_blockchain_address, validate_transaction_hash, validate_block_number
from django.utils.timezone import now

class Transaction(models.Model):
    """Represents a blockchain transaction relevant to the application, potentially containing events."""
    transaction_hash = models.CharField(
        max_length=66, 
        unique=True, 
        primary_key=True, # Use hash as primary key for easy linking
        validators=[validate_transaction_hash],
        help_text=_("Unique blockchain transaction hash (0x...)")
    )
    block_number = models.PositiveIntegerField(
        validators=[validate_block_number],
        db_index=True,
        help_text=_("Block number containing this transaction")
    )
    # Store the timestamp when the transaction was first seen or processed by the system
    # The block timestamp will be stored with the event
    created_at = models.DateTimeField(default=now, editable=False)
    # Potentially add sender/receiver if available from transaction data (not event data)
    # sender_address = models.CharField(max_length=42, validators=[validate_blockchain_address], null=True, blank=True)
    # receiver_address = models.CharField(max_length=42, validators=[validate_blockchain_address], null=True, blank=True)
    # gas_used = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-block_number"]
        verbose_name = _("Transaction")
        verbose_name_plural = _("Transactions")

    def __str__(self):
        return self.transaction_hash

class ContractEvent(models.Model):
    """Represents a specific event emitted by the TransactionContract smart contract."""
    # Link to the transaction that contained this event
    transaction = models.ForeignKey(
        Transaction, 
        on_delete=models.CASCADE, # Delete events if the transaction is deleted
        related_name="events",
        help_text=_("The transaction in which this event occurred")
    )
    log_index = models.PositiveIntegerField(
        help_text=_("Log index within the transaction receipt, ensuring uniqueness per transaction")
    )
    event_name = models.CharField(
        max_length=100,
        db_index=True,
        help_text=_("Name of the event emitted (e.g., TransactionSubmitted, ContractEvent)")
    )
    contract_address = models.CharField(
        max_length=42,
        validators=[validate_blockchain_address],
        db_index=True,
        help_text=_("Address of the contract that emitted the event")
    )
    # Block timestamp is more reliable than event timestamp for ordering
    block_timestamp = models.DateTimeField(
        help_text=_("Timestamp of the block containing the event")
    )
    is_fraudulent = models.BooleanField(
        default=False,
        db_index=True,
        help_text=_("Flag indicating if the event is suspected to be fraudulent")
    )
    # Stores all decoded arguments as JSON for flexibility and future use
    data = models.JSONField(
        help_text=_("Decoded event parameters/arguments as JSON")
    )

    # --- Specific fields extracted from data for easier querying (nullable) ---
    # Fields for TransactionSubmitted
    event_from_address = models.CharField(_("Event From Address"), max_length=42, validators=[validate_blockchain_address], null=True, blank=True, db_index=True)
    event_to_address = models.CharField(_("Event To Address"), max_length=42, validators=[validate_blockchain_address], null=True, blank=True, db_index=True)
    event_amount = models.DecimalField(_("Event Amount"), max_digits=78, decimal_places=0, null=True, blank=True)
    event_tx_hash_param = models.TextField(_("Event Tx Hash Parameter"), null=True, blank=True)

    # Fields for ContractEvent
    event_sender_address = models.CharField(_("Event Sender Address"), max_length=42, validators=[validate_blockchain_address], null=True, blank=True, db_index=True)
    event_message = models.TextField(_("Event Message"), null=True, blank=True)
    event_onchain_timestamp = models.PositiveBigIntegerField(_("Event On-Chain Timestamp"), null=True, blank=True)

    class Meta:
        ordering = ["-block_timestamp", "-log_index"]
        # Uniqueness constraint: Only one event per log index within a transaction
        unique_together = [("transaction", "log_index")]
        verbose_name = _("Contract Event")
        verbose_name_plural = _("Contract Events")

    def __str__(self):
        return f"{self.event_name} in Tx: {self.transaction_id[:10]}... (Log: {self.log_index})"

