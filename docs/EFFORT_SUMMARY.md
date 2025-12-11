# Effort Summary

This document summarizes the development journey of EIP Navigator, including exploration, challenges, and learnings.

---

## 🔍 Repositories & Resources Explored

### Datasets
| Resource | URL | Used? | Notes |
|----------|-----|-------|-------|
| ethereum/EIPs | https://github.com/ethereum/EIPs | ✅ Yes | Primary dataset (~500 EIP documents) |
| ethereum/ERCs | https://github.com/ethereum/ERCs | ❌ No | Initially considered, EIPs more comprehensive |
| OpenZeppelin Contracts | https://github.com/OpenZeppelin/openzeppelin-contracts | ❌ No | Good for Solidity examples, not standards docs |

### Embedding Models
| Model | Explored | Selected |
|-------|----------|----------|
| BAAI/bge-small-en-v1.5 | ✅ | ✅ |
| OpenAI text-embedding-3 | ✅ | ❌ (cost) |
| all-MiniLM-L6-v2 | ✅ | ❌ (quality) |

### Frameworks & Libraries
| Library | Purpose | Experience |
|---------|---------|------------|
| ChromaDB | Vector store | Excellent - simple API, good defaults |
| LangChain | Chunking utils | Used only text splitters |
| rank-bm25 | Keyword search | Lightweight, effective |
| sentence-transformers | Embeddings & reranking | Great cross-encoder support |
| FastAPI | API framework | Clean, async-friendly |

---

## ❌ What Didn't Work

### 1. Fixed-Size Chunking
**Attempt**: Used `RecursiveCharacterTextSplitter` with 1000-char chunks.  
**Problem**: Broke up EIP sections mid-sentence, causing poor retrieval.  
**Solution**: Switched to section-based chunking using markdown headers (`## `).

### 2. Vector-Only Retrieval  
**Attempt**: Pure semantic search with ChromaDB.  
**Problem**: Queries like "ERC-20" returned tangentially related EIPs instead of eip-20.md.  
**Solution**: Added BM25 keyword search + direct injection for explicit EIP mentions.

### 3. ERCs Repository First
**Attempt**: Started with ethereum/ERCs repo.  
**Problem**: Only ~200 documents, many cross-referenced EIPs not included.  
**Solution**: Switched to ethereum/EIPs which contains all standards.

### 4. Single-Pass Generation
**Attempt**: Generate response without validation.  
**Problem**: Solidity code sometimes had security issues (missing reentrancy guards).  
**Solution**: Added SecurityAuditorAgent with retry loop.

### 5. Cross-Encoder at Scale
**Attempt**: Rerank all 500+ chunks per query.  
**Problem**: Latency became unacceptable (>5 seconds).  
**Solution**: Pre-filter with vector + BM25, rerank only top candidates.

---

## ✅ What Worked Well

1. **Hybrid Retrieval (RRF)**: Combining vector + BM25 scores dramatically improved recall
2. **Section-Based Chunking**: Preserving markdown sections kept context intact
3. **Direct EIP Injection**: Pattern matching `ERC-20` → `eip-20.md` gave instant hits
4. **Cross-Encoder Reranking**: Significant precision boost on final candidates
5. **Audit Loop**: Self-correcting mechanism caught security issues

---

## 📚 What I Learned

### Technical Insights
- **Embedding choice matters less than retrieval strategy** - hybrid approaches beat pure semantic search
- **Chunking strategy is critical** - semantic splits > fixed-size splits
- **Reranking is underrated** - cross-encoders provide outsized quality gains
- **Explicit signals help** - pattern matching for known entities (ERC-X) is simple but effective

### Architecture Insights  
- **Multi-agent adds value** - separation of concerns (retrieval/generation/audit) is cleaner
- **Audit loops catch errors** - LLM-as-judge works for quality control
- **Dependency context helps** - adding "requires" metadata improved answers

### Development Process
- **Start simple, add complexity** - began with basic RAG, incrementally added features
- **Measure early** - `evaluate_metrics.py` helped identify retrieval gaps quickly
- **Containerize early** - Docker setup prevented "works on my machine" issues

---

## 🔗 References & Resources Used

| Resource | Description |
|----------|-------------|
| [ChromaDB Persistent Client](https://docs.trychroma.com/docs/run-chroma/persistent-client) | Documentation for setting up local persistent vector storage |
| [RAG Reranking with RRF](https://medium.com/@danushidk507/rag-vii-reranking-with-rrf-d8a13dba96de) | Blog explaining Reciprocal Rank Fusion for combining retrieval scores |
| [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) | HuggingFace page for the embedding model used in vector search |
| [Ethereum EIPs Repository](https://github.com/ethereum/EIPs/tree/master/EIPS) | Official GitHub source for all Ethereum Improvement Proposals |