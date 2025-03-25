from pydantic import BaseModel


class ScriptSig(BaseModel):
    asm: str
    hex: str


class VinItem(BaseModel):
    txid: str
    vout: int
    scriptSig: ScriptSig
    txinwitness: list[str]
    sequence: int


class ScriptPubKey(BaseModel):
    asm: str
    hex: str
    address: str
    type: str
    desc: str


class VoutItem(BaseModel):
    value: float
    n: int
    scriptPubKey: ScriptPubKey


class TransactionInfo(BaseModel):
    txid: str
    hash: str
    version: int
    size: int
    vsize: int
    weight: int
    locktime: int
    vin: list[VinItem]
    vout: list[VoutItem]
