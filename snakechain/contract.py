from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .parser import DSLParser
from .transpiler import SolidityTranspiler


@dataclass
class CompiledArtifact:
    abi: Any
    bytecode: str


class Contract:
    def __init__(self, source: str, name: str):
        self.source = source
        self.name = name
        self._compiled: Optional[CompiledArtifact] = None
        self._solidity_source: Optional[str] = None

    @classmethod
    def from_file(cls, path: str) -> "Contract":
        parser = DSLParser()
        spec = parser.parse_file(path)
        instance = cls(source=Path(path).read_text(), name=spec.name)
        instance._ast = spec
        return instance

    def compile(self, solc_version: str = "0.8.20") -> CompiledArtifact:
        try:
            from solcx import compile_standard, install_solc
        except ImportError as exc:
            raise ImportError("py-solc-x is required for compilation") from exc

        if not hasattr(self, "_ast"):
            spec = DSLParser().parse(self.source)
            self._ast = spec

        transpiler = SolidityTranspiler()
        self._solidity_source = transpiler.transpile(self._ast)

        install_solc(solc_version)
        compiled_sol = compile_standard(
            {
                "language": "Solidity",
                "sources": {f"{self.name}.sol": {"content": self._solidity_source}},
                "settings": {
                    "outputSelection": {
                        "*": {
                            "*": ["abi", "evm.bytecode"]
                        }
                    }
                },
            },
            solc_version=solc_version,
        )
        contract_interface = compiled_sol["contracts"][f"{self.name}.sol"][self.name]
        artifact = CompiledArtifact(
            abi=contract_interface["abi"],
            bytecode=contract_interface["evm"]["bytecode"]["object"],
        )
        self._compiled = artifact
        return artifact

    def deploy(self, rpc_url: str, private_key: str, gas: int = 3_000_000, chain_id: Optional[int] = None) -> Dict[str, Any]:
        try:
            from web3 import HTTPProvider, Web3
        except ImportError as exc:
            raise ImportError("web3.py is required for deployment") from exc

        if self._compiled is None:
            self.compile()

        w3 = Web3(HTTPProvider(rpc_url))
        account = w3.eth.account.from_key(private_key)
        contract = w3.eth.contract(abi=self._compiled.abi, bytecode=self._compiled.bytecode)
        construct_txn = contract.constructor().build_transaction(
            {
                "from": account.address,
                "gas": gas,
                "nonce": w3.eth.get_transaction_count(account.address),
                **({"chainId": chain_id} if chain_id else {}),
            }
        )
        signed = account.sign_transaction(construct_txn)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        return {
            "contract_address": receipt.contractAddress,
            "abi": self._compiled.abi,
            "deployer": account.address,
            "gas_used": receipt.gasUsed,
            "transaction_hash": tx_hash.hex(),
        }

    def solidity(self) -> str:
        if self._solidity_source:
            return self._solidity_source
        if hasattr(self, "_ast"):
            self._solidity_source = SolidityTranspiler().transpile(self._ast)
            return self._solidity_source
        raise ValueError("No transpiled source available. Parse or compile first.")
