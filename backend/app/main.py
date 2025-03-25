import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import requests
import json
import networkx as nx
from typing import Optional
from backend.models.btc_types import TransactionInfo
from networkx.readwrite import json_graph

load_dotenv()
RPC_USER = os.getenv("BITCOIN_RPC_USER")
RPC_PASSWORD = os.getenv("BITCOIN_RPC_PASSWORD")
RPC_URL = os.getenv("BITCOIN_RPC_URL")

app = FastAPI()

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    allow_credentials=True,
)


def call_rpc(method: str, params: list = []) -> Optional[dict]:
    auth_header = (RPC_USER, RPC_PASSWORD)
    payload = {
        "method": method,
        "params": params,
        "jsonrpc": "2.0",
        "id": 1,
    }

    try:
        response = requests.post(
            RPC_URL,
            auth=auth_header,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )

        if response.status_code != 200:
            raise HTTPException(500, f"RPC error: {response.text}")

        data = response.json()
        return data.get("result")
    except requests.exceptions.RequestException as e:
        raise HTTPException(500, f"Connection error: {str(e)}") from e
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"Invalid JSON response: {str(e)}") from e


def get_transaction_info(txid: str) -> Optional[TransactionInfo]:
    raw_tx = call_rpc("getrawtransaction", [txid])
    if not raw_tx:
        return None
    decoded_tx = call_rpc("decoderawtransaction", [raw_tx])
    return decoded_tx


def process_transaction(
    txid: str,
    max_depth: int,
    current_depth: int = 0,
    visited: Optional[set] = None,
    graph: Optional[nx.DiGraph] = None,
) -> nx.DiGraph:
    visited = visited or set()
    graph = graph or nx.DiGraph()

    if txid in visited or current_depth > max_depth:
        return graph

    visited.add(txid)
    tx_info = get_transaction_info(txid)

    if not tx_info:
        return graph

    graph.add_node(txid, **tx_info)  # Store full transaction details as node data

    for vin in tx_info.get("vin", []):
        prev_txid = vin.get("txid")
        if not prev_txid:
            continue

        try:
            prev_tx = get_transaction_info(prev_txid)
            scriptpubkey = prev_tx.get("vout")[vin["vout"]].get("scriptPubKey", {})

            edge_attrs = {
                "from_address": scriptpubkey.get("address"),
                "value": prev_tx["vout"][vin["vout"]].get("value"),
                "txid": prev_txid,
            }
            graph.add_edge(prev_txid, txid, **edge_attrs)

        except (KeyError, IndexError):
            pass  # Handle missing vout index gracefully

        if current_depth < max_depth:
            process_transaction(prev_txid, max_depth, current_depth + 1, visited, graph)

    return graph


@app.get("/api/v1/transaction/{txid}", status_code=200)
async def fetch_transaction_graph(txid: str, depth: int = 10) -> dict:
    if depth < 0:
        raise HTTPException(400, "Depth must be non-negative")

    graph = process_transaction(txid, depth)

    if not graph:
        raise HTTPException(404, "Transaction not found")

    return json_graph.node_link_data(graph)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5555)
