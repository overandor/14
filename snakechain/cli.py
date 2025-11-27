from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .contract import Contract


class SnakechainCLIError(Exception):
    """Raised when CLI operations fail."""


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SnakeChain DSL transpilation and compilation")
    parser.add_argument("dsl", help="Path to the DSL contract file")
    parser.add_argument(
        "-o",
        "--out",
        dest="out",
        help="Write Solidity output to this path instead of stdout",
    )
    parser.add_argument(
        "--compile",
        action="store_true",
        help="Compile the transpiled Solidity with solc to produce ABI and bytecode",
    )
    parser.add_argument(
        "--solc-version",
        default="0.8.20",
        help="solc version to install and use when --compile is set (default: 0.8.20)",
    )
    parser.add_argument(
        "--abi-out",
        help="Path to write the compiled ABI JSON when --compile is set",
    )
    parser.add_argument(
        "--bytecode-out",
        help="Path to write the compiled bytecode when --compile is set",
    )
    return parser.parse_args(argv)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        contract = Contract.from_file(args.dsl)
        solidity_source = contract.solidity()

        if args.out:
            _write_text(Path(args.out), solidity_source)
        else:
            sys.stdout.write(solidity_source)
            if not solidity_source.endswith("\n"):
                sys.stdout.write("\n")

        if args.compile:
            artifact = contract.compile(solc_version=args.solc_version)
            if args.abi_out:
                _write_text(Path(args.abi_out), json.dumps(artifact.abi, indent=2))
            if args.bytecode_out:
                _write_text(Path(args.bytecode_out), artifact.bytecode)
    except Exception as exc:  # noqa: BLE001
        raise SnakechainCLIError(str(exc)) from exc

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
