# OpenOSINT — Installation Guide

Step-by-step setup for [jebat8101/openOSINT](https://github.com/jebat8101/openOSINT).

> **Legal:** For authorized security research only. See [DISCLAIMER.md](DISCLAIMER.md).

---

## Requirements

- Python **3.10+**
- `git`
- Internet access (for API/binary tools)

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/jebat8101/openOSINT.git
cd openOSINT
```

---

## Step 2 — Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate    # Linux/macOS
# Windows: venv\Scripts\activate
```

---

## Step 3 — Install OpenOSINT

```bash
pip install --upgrade pip
pip install -e .
```

**Optional extras:**

```bash
pip install -e ".[all]"     # Shodan + Ollama client + PDF + Streamlit web UI
pip install -e ".[web]"     # Streamlit only
pip install -e ".[ollama]"  # Ollama Python client
pip install -e ".[shodan]"  # Shodan API client
```

---

## Step 4 — Install OSINT binaries

These must be available on `PATH` (inside the venv after `pip install`):

```bash
pip install holehe sherlock-project sublist3r
```

| Binary       | Purpose              |
|-------------|----------------------|
| `holehe`    | Email enumeration    |
| `sherlock`  | Username enumeration |
| `sublist3r` | Subdomain enumeration|
| `phoneinfoga` | Phone OSINT ([releases](https://github.com/sundowndev/phoneinfoga/releases)) |

Verify:

```bash
which holehe sherlock sublist3r
openosint --help
```

---

## Step 5 — Configure AI (choose one)

### Option A — Anthropic Claude (default)

1. Create an API key at [console.anthropic.com](https://console.anthropic.com/).
2. Export it:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Optional — persist in `~/.bashrc` or `~/.zshrc`:

```bash
echo 'export ANTHROPIC_API_KEY=sk-ant-...' >> ~/.zshrc
source ~/.zshrc
```

Or pass per run:

```bash
openosint --api-key sk-ant-...
```

> Requires API **credits** on your Anthropic account.

### Option B — Ollama (local, no Anthropic key)

1. Install the **Ollama server**: [ollama.com/download](https://ollama.com/download)
2. Start and pull a model:

```bash
ollama serve
ollama pull llama3.2
```

3. Install the Python client and run:

```bash
pip install ollama
openosint --provider ollama
```

---

## Step 6 — Optional API keys

```bash
export HIBP_API_KEY=...           # Have I Been Pwned — search_breach
export SHODAN_API_KEY=...         # Shodan — search_shodan
export VIRUSTOTAL_API_KEY=...     # VirusTotal — search_virustotal
export IPINFO_TOKEN=...           # ipinfo.io — higher IP lookup limits
```

---

## Step 7 — Verify installation

**Direct tool (no AI):**

```bash
openosint email target@example.com
openosint username johndoe99
```

**Interactive AI REPL:**

```bash
openosint
```

**Streamlit web UI** (if `[web]` installed):

```bash
streamlit run openosint/streamlit_app.py
# or:
openosint-web
```

Open http://localhost:8501

---

## Quick reference

| Command | Description |
|---------|-------------|
| `openosint` | AI-powered interactive REPL |
| `openosint email ADDR` | Email scan (holehe) |
| `openosint username USER` | Username scan (sherlock) |
| `openosint --parallel email ADDR` | Email + breach in parallel |
| `openosint --provider ollama` | Use local Ollama |
| `openosint multi targets.txt` | Multi-target investigation |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `openosint: command not found` | Activate `venv` or run `pip install -e .` |
| `ANTHROPIC_API_KEY is not set` | `export ANTHROPIC_API_KEY=...` |
| Credit balance too low | Add billing credits or use `openosint email ...` without AI |
| Ollama connection failed | Install/start Ollama **server**, not only `pip install ollama` |
| sublist3r DNSdumpster crash | Use OpenOSINT `search_domain` (stable engines + crt.sh) |
| `holehe` TypeError / dict args | Update to latest `openosint` (tool input normalization) |

---

## Docker (optional)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
docker compose up
```

See `docker-compose.yml` in the repo root.
