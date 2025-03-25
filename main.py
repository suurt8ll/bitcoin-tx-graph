import requests
import json
import os
from dotenv import load_dotenv
from btc_types import *

# Load environment variables from .env file
load_dotenv()

# Get RPC credentials from environment variables
RPC_USER = os.environ.get("BITCOIN_RPC_USER")
RPC_PASSWORD = os.environ.get("BITCOIN_RPC_PASSWORD")
RPC_URL = os.environ.get("BITCOIN_RPC_URL")

if not RPC_USER or not RPC_PASSWORD or not RPC_URL:
    print(
        "Error: Please set the BITCOIN_RPC_USER, BITCOIN_RPC_PASSWORD and BITCOIN_RPC_URL environment variables in .env."
    )
    exit(1)


def call_rpc(method=str, params=[]):
    """Calls a Bitcoin RPC method using JSON-RPC."""
    auth = (RPC_USER, RPC_PASSWORD)
    headers = {"content-type": "application/json"}
    payload = {
        "method": method,
        "params": params,
        "jsonrpc": "2.0",
        "id": 1,
    }
    try:
        response = requests.post(
            RPC_URL, auth=auth, headers=headers, data=json.dumps(payload)
        )
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()["result"]
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None
    except json.JSONDecodeError as e:
        print(
            f"JSON Decode Error: {e}. Response text: {response.text}"
        )  # Print the raw response
        return None
    except KeyError as e:
        print(f"KeyError: {e}.  Check the response structure.")
        return None


def get_transaction_info(txid: str) -> TransactionInfo:
    """Fetches and returns information about a specific transaction."""
    try:
        # First, get the raw transaction hex
        raw_tx = call_rpc("getrawtransaction", [txid])
        if not raw_tx:
            print(f"Error: Could not retrieve raw transaction for txid: {txid}")
            return None

        # Then, decode the raw transaction
        decoded_tx = call_rpc("decoderawtransaction", [raw_tx])
        if not decoded_tx:
            print(f"Error: Could not decode raw transaction for txid: {txid}")
            return None

        return decoded_tx

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None


def main():
    """Main function to get transaction info from user input."""
    txid = input("Enter the transaction ID (txid): ")

    transaction_info = get_transaction_info(txid)

    if transaction_info:
        print("\nTransaction Information:")
        for key, value in transaction_info.items():
            print(f"  {key}: {value}")
    else:
        print("Failed to retrieve transaction information.")


if __name__ == "__main__":
    main()
