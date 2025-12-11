# EIP Navigator 🧭

A Multi-Agent RAG (Retrieval-Augmented Generation) system for navigating Ethereum Improvement Proposals (ERCs) with built-in security auditing.

## ✨ Features

- **500+ ERC Standards** - Automatically fetches and indexes from [ethereum/ERCs](https://github.com/ethereum/ERCs)
- **Hybrid Search** - Combines Vector Search (BGE) + Keyword Search (BM25) + Direct Injection
- **Multi-Agent Architecture**:
  - 📚 **Librarian Agent** - Retrieves relevant ERC context
  - 🔧 **Interface Engineer Agent** - Generates Solidity code
  - 🛡️ **Security Auditor Agent** - Reviews code for vulnerabilities
- **Self-Correcting Loop** - Auditor finds issues → Engineer fixes → Up to 2 iterations
- **Live Quality Metrics** - Each response includes precision scoring

---

## 📋 Prerequisites

- **Python 3.9+**
- **OpenAI API Key** (for GPT-4o-mini)
- **Docker** (optional, for containerized deployment)

---

## 🚀 Quick Start (Local)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/eip-navigator.git
cd eip-navigator

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Create .env file from example
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here
```

### 3. Fetch ERC Documents

```bash
python fetch_docs.py
```

This downloads ~500 ERC markdown files from the official Ethereum repository to `./data/`.

### 4. Build the Index

```bash
python ingest.py
```

This creates:
- `./chroma_db/` - Vector embeddings (ChromaDB)
- `./bm25_index.pkl` - Keyword index + Dependency graph

**Note:** First run takes 5-10 minutes for embedding generation.

### 5. Start the Server

```bash
python main.py
```

Server runs at: **http://localhost:8123**

---

## 🐳 Docker Deployment

### Option A: Using Docker Compose (Recommended)

```bash
# Make sure Docker Desktop is running!

# Build and run
docker-compose up --build

# The container will automatically:
# 1. Fetch ERC documents
# 2. Build indexes
# 3. Start the server
```

### Option B: Manual Docker Build

```bash
# Build the image
docker build -t eip-navigator .

# Run with OpenAI API key
docker run -p 8123:8123 \
  -e OPENAI_API_KEY=sk-your-key-here \
  -v eip_data:/app/data \
  -v eip_chroma:/app/chroma_db \
  eip-navigator
```

---

## 📡 API Usage

### Endpoint: `POST /query`

**Request:**
```bash
curl -X POST "http://localhost:8123/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain the transferFrom workflow in ERC-20"}'
```

**Response:**
```json
{
  "query": "Explain the transferFrom workflow in ERC-20",
  "final_response": "```solidity\n// SPDX-License-Identifier: MIT\npragma solidity ^0.8.0;\n\ninterface IERC20 {\n    function transferFrom(...) external returns (bool);\n    ...\n}\n```",
  "audit_trail": [
    {
      "attempt": 1,
      "status": "PASS",
      "feedback": "No security issues found."
    }
  ],
  "retrieval_count": 5,
  "retrieved_documents": [
    {"source": "erc-20.md", "title": "Token Standard", "chunk_index": 2}
  ],
  "quality_metrics": {
    "relevant_count": 4,
    "total_count": 5,
    "precision": 0.8
  }
}
```

---

## 🔬 Example Queries

### 1. Standard Interface Generation
```bash
curl -X POST "http://localhost:8123/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Create an IERC721 interface"}'
```

### 2. Security-Focused Query
```bash
curl -X POST "http://localhost:8123/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Create a vault with withdraw function"}'
```
*The Auditor will catch re-entrancy vulnerabilities and fix them!*

### 3. Dependency-Aware Query
```bash
curl -X POST "http://localhost:8123/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "What does ERC-721 require from ERC-165?"}'
```

---

## 📊 Evaluation

Run the built-in metrics script:

```bash
python evaluate_metrics.py
```

**Sample Output:**
```
Query                          | Expected        | Rank found | Status
----------------------------------------------------------------------
ERC-20 Token Standard          | eip-20.md       | 1          | HIT
Non-Fungible Token NFT         | eip-721.md      | 1          | HIT
Tokenized Vault Standard       | eip-4626.md     | 1          | HIT
EIP-1 definition               | eip-1.md        | 1          | HIT
Hardfork Meta                  | eip-1.md        | -          | MISS

==============================
Recall@5: 80.0%
Latency: 0.11s
==============================
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Request                          │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   main.py (Orchestrator)                     │
│                      FastAPI on :8123                        │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              LibrarianAgent (agents.py)                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐    │
│  │ Direct      │ │ Vector      │ │ BM25                │    │
│  │ Injection   │ │ Search      │ │ Keyword Search      │    │
│  │ (ERC-X→erc- │ │ (ChromaDB + │ │ (rank_bm25)         │    │
│  │  X.md)      │ │  BGE-Small) │ │                     │    │
│  └──────┬──────┘ └──────┬──────┘ └──────────┬──────────┘    │
│         └───────────────┼───────────────────┘               │
│                         ▼                                    │
│              Reciprocal Rank Fusion (RRF)                    │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│           InterfaceEngineerAgent (agents.py)                 │
│                   GPT-4o-mini                                │
│              "Senior Solidity Engineer"                      │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────┐
│           SecurityAuditorAgent (agents.py)                   │
│                   GPT-4o-mini                                │
│           "Smart Contract Security Auditor"                  │
│  Checks: Re-entrancy, Overflow, Access Control, Logic        │
└─────────────────────────┬───────────────────────────────────┘
                          ▼
                   PASS? ──────────► Return Response
                     │
                     ▼ FAIL (max 2 retries)
            Engineer.refine(feedback)
```

---

## 📁 Project Structure

```
EIP Navigator/
├── main.py              # FastAPI orchestrator
├── agents.py            # LibrarianAgent, EngineerAgent, AuditorAgent
├── ingest.py            # Data pipeline (chunking, embedding, indexing)
├── fetch_docs.py        # Downloads ERCs from GitHub
├── evaluate_metrics.py  # Recall@K evaluation script
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
├── Dockerfile           # Container definition
├── docker-compose.yml   # Docker orchestration
├── entrypoint.sh        # Docker startup script
├── project_deep_dive.md # Detailed architecture documentation
├── version.md           # Change log
├── notes.debug          # Debug file (required by spec)
├── data/                # Downloaded ERC markdown files
├── chroma_db/           # Vector database (generated)
└── bm25_index.pkl       # Keyword index (generated)
```

---

## ⚙️ Configuration

| Environment Variable | Description | Required |
|---------------------|-------------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | ✅ Yes |
| `TOKENIZERS_PARALLELISM` | Set to `false` to suppress HuggingFace warnings | Optional |

---

## 🐛 Troubleshooting

### "bm25_index.pkl not found"
Run the ingestion pipeline:
```bash
python ingest.py
```

### "Cannot connect to Docker daemon"
Start Docker Desktop before running docker-compose.

### "Address already in use (port 8123)"
Kill the existing process:
```bash
lsof -t -i:8123 | xargs kill -9
```

### Low Recall/Precision
- Ensure you're using explicit ERC numbers in queries (e.g., "ERC-20" not just "token standard")
- Re-run `python ingest.py` to rebuild indexes

---


## 🙏 Acknowledgments

- [Ethereum EIPs/ERCs Repository](https://github.com/ethereum/ERCs)
- [ChromaDB](https://www.trychroma.com/)
- [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5)
- [OpenAI GPT-4o-mini](https://openai.com/)
