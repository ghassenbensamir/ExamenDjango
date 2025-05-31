# /home/ubuntu/web3_project/api/tasks.py

from celery import shared_task
from web3 import Web3
from django.conf import settings
from .models import Transaction, ContractEvent # Import both models
from .validators import validate_blockchain_address, validate_transaction_hash, validate_block_number
import json
import logging
from datetime import datetime
from django.utils.timezone import make_aware
import random # For placeholder AI
from decimal import Decimal # To handle uint256 amount
from django.db import transaction as db_transaction # For atomic operations

logger = logging.getLogger(__name__)

# --- Placeholder AI Fraud Detection (Remains the same, acts on event data) --- 
def detect_fraud(event_name, event_log, decoded_args):
    """
    Placeholder function for AI-based fraud detection.
    Adapt rules based on the new event structures.
    """
    logger.debug(f"Running fraud check for event: {event_name}")
    is_fraudulent = False
    tx_hash = event_log.get("transactionHash", b"").hex()

    # Example Rule 1: Check for unusually high amounts in TransactionSubmitted
    if event_name == "TransactionSubmitted" and decoded_args:
        try:
            amount = decoded_args.get("amount")
            if amount is not None and isinstance(amount, int):
                fraud_threshold = Decimal(10**24) 
                if Decimal(amount) > fraud_threshold:
                    logger.warning(f"Potential fraud detected: High amount ({amount}) in TransactionSubmitted event. Tx: {tx_hash}")
                    is_fraudulent = True
        except Exception as e:
            logger.error(f"Error during fraud check amount extraction: {e}")

    # Example Rule 2: Check for specific keywords in ContractEvent message
    if event_name == "ContractEvent" and decoded_args:
        try:
            message = decoded_args.get("message", "")
            if "phishing attempt" in message.lower():
                 logger.warning(f"Potential fraud detected: Suspicious message in ContractEvent. Tx: {tx_hash}")
                 is_fraudulent = True
        except Exception as e:
             logger.error(f"Error during fraud check message extraction: {e}")

    if is_fraudulent:
        logger.info(f"Fraud check result for Tx {tx_hash}: SUSPECTED")
    else:
        logger.debug(f"Fraud check result for Tx {tx_hash}: OK")

    return is_fraudulent

# --- Helper function to get block timestamp --- 
def get_block_timestamp(w3, block_number):
    try:
        block_info = w3.eth.get_block(block_number)
        return make_aware(datetime.fromtimestamp(block_info["timestamp"]))
    except Exception as e:
        logger.error(f"Could not get timestamp for block {block_number}: {e}")
        return make_aware(datetime.now()) # Fallback

@shared_task
def poll_contract_events(start_block_offset=100):
    """
    Polls for TransactionSubmitted and ContractEvent events from the TransactionContract.
    Creates Transaction records if they don't exist.
    Creates ContractEvent records linked to their Transaction.
    Performs fraud detection (placeholder) and stores events in the database.
    """
    logger.info("Starting TransactionContract event polling task (Separate Models)... ")

    # --- Web3 Setup --- 
    GANACHE_URL = getattr(settings, "GANACHE_URL", "http://127.0.0.1:7545")
    CONTRACT_ADDRESS = getattr(settings, "TRANSACTION_CONTRACT_ADDRESS", None)
    CONTRACT_ABI_PATH = getattr(settings, "TRANSACTION_CONTRACT_ABI_PATH", None)

    if not CONTRACT_ADDRESS or not CONTRACT_ABI_PATH:
        logger.error("TRANSACTION_CONTRACT_ADDRESS or ABI path not configured. Aborting poll.")
        return "Configuration Error"

    try:
        w3 = Web3(Web3.HTTPProvider(GANACHE_URL))
        if not w3.is_connected():
            logger.error(f"Failed to connect to Web3 provider at {GANACHE_URL}. Aborting poll.")
            return "Connection Error"

        with open(CONTRACT_ABI_PATH, "r") as abi_file:
            abi_data = json.load(abi_file)
            contract_abi = abi_data if isinstance(abi_data, list) else abi_data.get("abi")
            if not contract_abi:
                 raise ValueError("ABI array not found in JSON file.")
        contract_instance = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)
        logger.info(f"Contract instance created for TransactionContract at: {CONTRACT_ADDRESS}")

    except Exception as e:
        logger.error(f"Error initializing Web3 or contract: {e}. Aborting poll.")
        return f"Initialization Error: {e}"

    # --- Define Block Range --- 
    try:
        latest_block = w3.eth.block_number
        from_block = max(0, latest_block - start_block_offset)
        to_block = latest_block
        logger.info(f"Scanning for events from block {from_block} to {to_block}")
    except Exception as e:
        logger.error(f"Could not get latest block number: {e}. Aborting poll.")
        return "Block Number Error"

    # --- Process Events --- 
    processed_count = 0
    fraud_detected_count = 0
    event_names_to_poll = ["TransactionSubmitted", "ContractEvent"]

    for event_name in event_names_to_poll:
        try:
            logger.debug(f"Polling for {event_name} events...")
            event_interface = getattr(contract_instance.events, event_name, None)
            if not event_interface:
                logger.warning(f"{event_name} event not found in contract ABI. Skipping.")
                continue

            event_filter = event_interface.create_filter(fromBlock=from_block, toBlock=to_block)
            events = event_filter.get_all_entries()
            logger.debug(f"Found {len(events)} raw logs for {event_name}.")

            for event_log in events:
                try:
                    tx_hash = event_log["transactionHash"].hex()
                    block_num = event_log["blockNumber"]
                    log_index = event_log["logIndex"]

                    # Use atomic transaction to ensure Transaction and ContractEvent are created/updated together
                    with db_transaction.atomic():
                        # Get or create the Transaction record
                        transaction_obj, created = Transaction.objects.get_or_create(
                            transaction_hash=tx_hash,
                            defaults={"block_number": block_num} # Set block_number on creation
                        )
                        # Update block_number if transaction already existed but was found in a later block (unlikely but possible)
                        if not created and transaction_obj.block_number < block_num:
                            transaction_obj.block_number = block_num
                            transaction_obj.save()
                        
                        # Check if this specific event log already exists for this transaction
                        if ContractEvent.objects.filter(transaction=transaction_obj, log_index=log_index).exists():
                            # logger.debug(f"Event {event_name} from tx {tx_hash[:10]}... log index {log_index} already exists. Skipping.")
                            continue

                        # Decode event
                        decoded_log = event_interface.process_log(event_log)
                        decoded_args = dict(decoded_log["args"])

                        # Basic validation (already done in model, but good practice)
                        validate_transaction_hash(tx_hash)
                        validate_block_number(block_num)

                        # --- AI Fraud Detection Call --- 
                        is_fraudulent = detect_fraud(event_name, dict(event_log), decoded_args)
                        if is_fraudulent:
                            fraud_detected_count += 1
                        # --------------------------------

                        block_timestamp = get_block_timestamp(w3, block_num)
                        
                        # Prepare data for ContractEvent model instance
                        event_data_for_model = {
                            "transaction": transaction_obj, # Link to the Transaction object
                            "log_index": log_index,
                            "event_name": event_name,
                            "contract_address": Web3.to_checksum_address(CONTRACT_ADDRESS),
                            "block_timestamp": block_timestamp,
                            "is_fraudulent": is_fraudulent,
                            "data": json.dumps(decoded_args, default=str), # Store decoded args as JSON
                        }

                        # Populate specific fields based on event type
                        if event_name == "TransactionSubmitted":
                            event_data_for_model["event_from_address"] = decoded_args.get("from")
                            event_data_for_model["event_to_address"] = decoded_args.get("to")
                            amount_val = decoded_args.get("amount")
                            event_data_for_model["event_amount"] = Decimal(amount_val) if amount_val is not None else None
                            event_data_for_model["event_tx_hash_param"] = decoded_args.get("txHash")
                        elif event_name == "ContractEvent":
                            event_data_for_model["event_sender_address"] = decoded_args.get("sender")
                            event_data_for_model["event_message"] = decoded_args.get("message")
                            event_data_for_model["event_onchain_timestamp"] = decoded_args.get("timestamp")

                        # Create the event record in DB
                        ContractEvent.objects.create(**event_data_for_model)
                        processed_count += 1
                        logger.info(f"Stored event {event_name} for tx {tx_hash[:10]}... log index {log_index}. Fraud check: {'SUSPECTED' if is_fraudulent else 'OK'}")

                except Exception as e:
                    logger.error(f"Error processing individual {event_name} log: {event_log}. Error: {e}", exc_info=True)
        
        except Exception as e:
             logger.error(f"Error filtering or processing {event_name} events: {e}", exc_info=True)

    logger.info(f"Event polling task finished. Processed {processed_count} new events. Found {fraud_detected_count} potentially fraudulent events.")
    return f"Processed {processed_count} new events. Flagged {fraud_detected_count} as potentially fraudulent."

# --- How to run manually --- 
# 1. Ensure Django migrations for the Transaction and ContractEvent models are applied.
#    - python manage.py makemigrations api
#    - python manage.py migrate
# 2. Ensure Broker and Celery worker are running.
#    - celery -A web3_project worker -l info
# 3. Open Django shell:
#    - python manage.py shell
# 4. Import and run the task:
#    - from api.tasks import poll_contract_events
#    - poll_contract_events.delay() 

