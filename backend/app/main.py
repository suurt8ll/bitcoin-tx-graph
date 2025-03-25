from typing import Optional
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
import requests
import json
import networkx as nx
from backend.models.transactions import TransactionInfo
from networkx.readwrite import json_graph

load_dotenv()
RPC_USER = os.getenv("BITCOIN_RPC_USER")
RPC_PASSWORD = os.getenv("BITCOIN_RPC_PASSWORD")
RPC_URL = os.getenv("BITCOIN_RPC_URL")

app = FastAPI()

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
    if not decoded_tx:
        return None
    try:
        return TransactionInfo(**decoded_tx)
    except Exception:
        return None


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

    graph.add_node(txid, **tx_info.model_dump())

    for vin in tx_info.vin:
        prev_txid = vin.txid
        if not prev_txid:
            continue

        try:
            prev_tx = get_transaction_info(prev_txid)
            if not prev_tx:
                continue

            vout_index = vin.vout
            prev_vout = prev_tx.vout[vout_index]
            scriptpubkey = prev_vout.scriptPubKey

            edge_attrs = {
                "from_address": scriptpubkey.address,
                "value": prev_vout.value,
                "txid": prev_txid,
            }
            graph.add_edge(prev_txid, txid, **edge_attrs)

        except (IndexError, AttributeError):
            continue

        if current_depth < max_depth:
            process_transaction(prev_txid, max_depth, current_depth + 1, visited, graph)

    return graph


@app.get("/api/v1/transaction/{txid}", status_code=200)
async def fetch_transaction_graph(txid: str, depth: int = 3) -> dict:
    if depth < 0:
        raise HTTPException(400, "Depth must be non-negative")
    if depth > 5:
        raise HTTPException(400, "Depth must not exceed 5 due to resource constraints")

    graph = process_transaction(txid, depth)

    if not any(graph.nodes):
        raise HTTPException(404, "Transaction not found")

    return json_graph.node_link_data(graph)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5555)
