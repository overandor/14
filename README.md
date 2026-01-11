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

### CLI usage

Transpile a DSL contract to Solidity from the command line:

```
python -m snakechain examples/erc20.dsl -o build/ERC20.sol
```

To emit to stdout instead of a file:

```
python -m snakechain examples/erc20.dsl
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

### Realization-Only DAG (human-in-the-loop pipeline)

`snakechain.dag` provides a minimal execution engine for a four-stage pipeline that enforces a proofable human gate before any downstream steps run. Pipelines are declared in YAML and must start with `fetch_data` → `human_gate` → `signal_generator` → `profit_evaluator`.

Run a pipeline definition:

```
python - <<'PY'
from pathlib import Path
from snakechain import RealizationDagRunner, load_pipeline

pipeline = load_pipeline(Path('examples/pipeline.yaml'))
runner = RealizationDagRunner(pipeline, block_for_proof=False)
runner.run()
PY
```

To satisfy the human gate in `examples/pipeline.yaml`, write `approved` into `artifacts/proof.txt` before execution.

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

Continuous integration runs the same test suite on pushes and pull requests to `work` using GitHub Actions (`.github/workflows/ci.yml`).

## Deployment status

No smart contract toolchain is present (no Hardhat config, Foundry config, or `contracts/` directory), and no frontend framework is scaffolded (no `package.json`, `src/`, or `app/` structure). Contract or UI deployment is not possible until those components are added. See `DEPLOYMENT_STATUS.md` for a concise assessment.
