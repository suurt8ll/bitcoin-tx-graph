from typing import TypedDict


class ScriptSig(TypedDict):
    asm: str
    hex: str


class VinItem(TypedDict):
    txid: str
    vout: int
    scriptSig: ScriptSig
    txinwitness: list[str]
    sequence: int


class ScriptPubKey(TypedDict):
    asm: str
    hex: str
    address: str
    type: str
    desc: str


class VoutItem(TypedDict):
    value: float
    n: int
    scriptPubKey: ScriptPubKey


class TransactionInfo(TypedDict):
    txid: str
    hash: str
    version: int
    size: int
    vsize: int
    weight: int
    locktime: int
    vin: list[VinItem]
    vout: list[VoutItem]
