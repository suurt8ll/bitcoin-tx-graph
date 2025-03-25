import requests
import json
import os
from dotenv import load_dotenv
from typing import Optional
from btc_types import TransactionInfo

# Load environment variables
load_dotenv()
RPC_USER = os.environ.get("BITCOIN_RPC_USER")
RPC_PASSWORD = os.environ.get("BITCOIN_RPC_PASSWORD")
RPC_URL = os.environ.get("BITCOIN_RPC_URL")

if not RPC_USER or not RPC_PASSWORD or not RPC_URL:
    print(
        "Error: Set BITCOIN_RPC_USER, BITCOIN_RPC_PASSWORD, and BITCOIN_RPC_URL in .env"
    )
    exit(1)


def call_rpc(method: str, params: list = []) -> Optional[dict]:
    """Calls a Bitcoin RPC method."""
    auth = (RPC_USER, RPC_PASSWORD)
    headers = {"content-type": "application/json"}
    payload = {"method": method, "params": params, "jsonrpc": "2.0", "id": 1}
    try:
        response = requests.post(
            RPC_URL, auth=auth, headers=headers, data=json.dumps(payload)
        )
        response.raise_for_status()
        return response.json()["result"]
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        print(f"JSON/Key error: {e}")
        return None


def get_transaction_info(txid: str) -> Optional[TransactionInfo]:
    """Fetches and returns decoded transaction info."""
    raw_tx = call_rpc("getrawtransaction", [txid])
    if not raw_tx:
        return None
    decoded_tx = call_rpc("decoderawtransaction", [raw_tx])
    return decoded_tx


def process_transaction(
    txid: str,
    max_depth: int,
    current_depth: int = 0,
    visited: Optional[set[str]] = None,
) -> None:
    """
    Recursively processes transactions up to the specified depth.
    Args:
        txid: Transaction ID to process
        max_depth: Maximum recursion depth
        current_depth: Current recursion level (starts at 0)
        visited: Set of already processed txids to prevent cycles
    """
    if visited is None:
        visited = set()

    # Base cases
    if current_depth > max_depth:
        return
    if txid in visited:
        return
    visited.add(txid)

    tx_info = get_transaction_info(txid)
    if not tx_info:
        print(f"⚠️ Could not retrieve transaction: {txid}")
        return

    print(f"\n{'-'*40}\nTransaction: {txid}\n{'-'*40}")

    # Process Inputs
    print("Inputs:")
    for vin in tx_info.get("vin", []):
        prev_txid = vin["txid"]
        vout_index = vin["vout"]

        prev_tx = get_transaction_info(prev_txid)
        if not prev_tx:
            print(f"  🔹 Previous TX {prev_txid} not found")
            continue

        try:
            prev_vout = prev_tx["vout"][vout_index]
            prev_address = prev_vout["scriptPubKey"]["address"]
            amount = prev_vout["value"]
            print(f"  🔹 From: {prev_address} (Amount: {amount:.8f} BTC)")
        except IndexError:
            print(f"  🔹 Invalid vout index {vout_index} for TX {prev_txid}")

    # Process Outputs
    print("\nOutputs:")
    for vout in tx_info.get("vout", []):
        address = vout["scriptPubKey"]["address"]
        value = vout["value"]
        print(f"  🔸 To: {address} (Amount: {value:.8f} BTC)")

    # Recurse into inputs if depth allows
    if current_depth < max_depth:
        for vin in tx_info.get("vin", []):
            prev_txid = vin["txid"]
            process_transaction(prev_txid, max_depth, current_depth + 1, visited)


def main():
    txid = input("Enter Bitcoin transaction ID (txid): ").strip()
    while True:
        try:
            depth = int(input("Enter recursion depth (integer): "))
            if depth < 0:
                raise ValueError("Depth must be non-negative")
            break
        except ValueError as e:
            print(f"⚠️ {e}. Please enter a valid integer.")

    print(f"\nStarting analysis for TX {txid} with depth {depth}")
    process_transaction(txid, depth)


if __name__ == "__main__":
    main()
