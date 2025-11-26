# Repository Factory

A minimal Flask application for spinning up pre-initialized Git repositories with standardized launch metadata. It now also ships a SnakeChain prototype: a Python DSL → Solidity transpilation toolchain with optional compilation and deployment hooks.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Navigate to `http://localhost:8000` and submit the form to generate repositories. The app initializes Git, writes a README with launch destinations, and seeds a `.gitignore` for each repository.

## SnakeChain DSL Tooling

The `snakechain` package converts a restricted Python-style DSL into Solidity and provides optional compilation/deployment helpers.

### Quick check

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest tests/test_snakechain.py
```

### Example

```
from snakechain import Contract

c = Contract.from_file("examples/erc20.dsl")
solidity_source = c.solidity()
# optional compilation if solc is available
# artifact = c.compile()
# deployment requires RPC URL + private key
# c.deploy(rpc_url, private_key)
```

DSL example: `examples/erc20.dsl`

```
contract ERC20:
    name: string = "Token"
    symbol: string = "TKN"
    totalSupply: uint256 = 1000000
    balances: mapping[address,uint256]

    def transfer(to: address, amount: uint256):
        assert self.balances[msg.sender] >= amount
        self.balances[msg.sender] = self.balances[msg.sender] - amount
        self.balances[to] = self.balances[to] + amount
```

## Configuration

- **Count** – number of repositories to create in a single run (bounded by form controls).
- **Prefix** – base name; sequential strategy appends a numeric suffix, random strategy appends an 8-character hash.
- **Naming Strategy** – sequential or random.
- **Start Index** – first index for sequential naming.

Repositories are emitted under `generated_repos/`. Each includes:

- `README.md` with launch links for Google Colab, Hugging Face Spaces, Replicate, Modal, Vercel, Render, and Netlify.
- `.gitignore` with Python and editor defaults.
- A fresh Git repository initialized via `git init`.

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

## CI

A GitHub Actions workflow at `.github/workflows/ci.yml` installs `requirements-dev.txt` and runs `pytest` on pushes and pull requests targeting the `work` branch to keep the SnakeChain pipeline and repository factory exercised in automation.
