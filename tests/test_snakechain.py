import pathlib

from snakechain import Contract, DSLParser, SolidityTranspiler


def test_parse_contract_example():
    parser = DSLParser()
    spec = parser.parse(pathlib.Path("examples/erc20.dsl").read_text())
    assert spec.name == "ERC20"
    assert {v.name for v in spec.state_vars} == {"name", "symbol", "totalSupply", "balances"}
    transfer = next(fn for fn in spec.functions if fn.name == "transfer")
    assert [p.name for p in transfer.parameters] == ["to", "amount"]
    assert len(transfer.body) == 3


def test_transpile_solidity_includes_require_and_assignment():
    parser = DSLParser()
    spec = parser.parse(pathlib.Path("examples/erc20.dsl").read_text())
    solidity = SolidityTranspiler().transpile(spec)
    assert "pragma solidity" in solidity
    assert "require(self.balances[msg.sender] >= amount" not in solidity
    assert "require(self" not in solidity
    assert "require(balances[msg.sender]" in solidity
    assert "balances[msg.sender] = balances[msg.sender] - amount;" in solidity
    assert "function transfer(address to, uint256 amount) public" in solidity
