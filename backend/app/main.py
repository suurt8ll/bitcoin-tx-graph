import logging
import colorlog
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

# Logging configuration
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "WARNING").upper()
LOG_LEVEL = getattr(logging, LOG_LEVEL_STR, logging.WARNING)

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        "%(asctime)s %(log_color)s%(levelname)s%(reset)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red",
        },
    )
)

logger = colorlog.getLogger()
logger.addHandler(handler)
logger.setLevel(LOG_LEVEL)

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
    logging.debug(f"Calling RPC method {method} with params {params}")
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
            logging.error(f"RPC error {response.status_code}: {response.text}")
            raise HTTPException(500, f"RPC error: {response.text}")

        data = response.json()
        logging.debug(f"RPC response: {data}")
        return data.get("result")
    except requests.exceptions.RequestException as e:
        logging.error(f"Request exception: {str(e)}")
        raise HTTPException(500, f"Connection error: {str(e)}") from e
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON response: {str(e)}")
        raise HTTPException(400, f"Invalid JSON response: {str(e)}") from e


def get_transaction_info(txid: str) -> Optional[TransactionInfo]:
    logging.debug(f"Retrieving transaction info for {txid}")
    raw_tx = call_rpc("getrawtransaction", [txid])
    if not raw_tx:
        logging.warning(f"Failed to get raw transaction for {txid}")
        return None

    decoded_tx = call_rpc("decoderawtransaction", [raw_tx])
    if not decoded_tx:
        logging.warning(f"Failed to decode transaction {txid}")
        return None

    try:
        tx_info = TransactionInfo(**decoded_tx)
        logging.debug(f"Successfully parsed transaction {txid}")
        return tx_info
    except Exception as e:
        logging.error(f"Error creating TransactionInfo: {str(e)}")
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
        logging.debug(
            f"Skipping {txid} (visited={txid in visited}, depth={current_depth}/{max_depth})"
        )
        return graph

    visited.add(txid)
    logging.info(f"Processing txid {txid} at depth {current_depth}")

    tx_info = get_transaction_info(txid)
    if not tx_info:
        logging.warning(f"Transaction {txid} not found or invalid")
        return graph

    graph.add_node(txid, **tx_info.model_dump())
    logging.debug(f"Added node {txid}")

    for vin in tx_info.vin:
        prev_txid = vin.txid
        if not prev_txid:
            continue

        try:
            prev_tx = get_transaction_info(prev_txid)
            if not prev_tx:
                logging.warning(f"Previous transaction {prev_txid} not found")
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
            logging.debug(
                f"Added edge {prev_txid}->{txid} with value {prev_vout.value}"
            )

        except (IndexError, AttributeError) as e:
            logging.error(f"Error processing input {vin}: {str(e)}", exc_info=True)
            continue

        if current_depth < max_depth:
            logging.debug(f"Recursing to {prev_txid} (depth {current_depth + 1})")
            process_transaction(prev_txid, max_depth, current_depth + 1, visited, graph)

    return graph


@app.get("/api/v1/transaction/{txid}", status_code=200)
async def fetch_transaction_graph(txid: str, depth: int = 3) -> dict:
    logging.info(f"Handling request for txid {txid} with depth {depth}")

    if depth < 0:
        logging.warning(f"Invalid depth {depth} for txid {txid}")
        raise HTTPException(400, "Depth must be non-negative")

    if depth > 5:
        logging.warning(f"Depth {depth} exceeds limit for txid {txid}")
        raise HTTPException(400, "Depth must not exceed 5")

    graph = process_transaction(txid, depth)

    if not any(graph.nodes):
        logging.warning(f"Transaction {txid} not found in network")
        raise HTTPException(404, "Transaction not found")

    logging.info(
        f"Returning graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges"
    )
    return json_graph.node_link_data(graph, edges="edges")


if __name__ == "__main__":
    logging.info("Starting FastAPI server")
    uvicorn.run(app, host="0.0.0.0", port=5555)
