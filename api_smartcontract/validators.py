import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

def validate_blockchain_address(value):
    """Validate that the value is a valid Ethereum address."""
    if not isinstance(value, str) or not re.match(r'^0x[a-fA-F0-9]{40}$', value):
        raise ValidationError(
            _('%(value)s is not a valid blockchain address'),
            params={'value': value},
        )

def validate_transaction_hash(value):
    """Validate that the value is a valid Ethereum transaction hash."""
    if not isinstance(value, str) or not re.match(r'^0x[a-fA-F0-9]{64}$', value):
        raise ValidationError(
            _('%(value)s is not a valid transaction hash'),
            params={'value': value},
        )

def validate_block_number(value):
    """Validate that the value is a non-negative integer."""
    if not isinstance(value, int) or value < 0:
        raise ValidationError(
            _('%(value)s is not a valid block number (must be a non-negative integer)'),
            params={'value': value},
        )

