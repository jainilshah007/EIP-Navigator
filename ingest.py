import os
import re
import pickle
import chromadb
from chromadb.utils import embedding_functions
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rank_bm25 import BM25Okapi
import yaml

def extract_frontmatter(text):
    pattern = r'^---\n(.*?)\n---\n'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return {}
    return {}

def split_by_sections(text):
    """Split markdown by headers, keeping each section together"""
    sections = re.split(r'\n(?=## )', text)
    chunks = []
    for section in sections:
        if len(section.strip()) > 100:
            if len(section) > 2000:
                # fallback: split large sections
                for i in range(0, len(section), 1500):
                    chunks.append(section[i:i+1500])
            else:
                chunks.append(section.strip())
    return chunks if chunks else [text[:1500]]

def ingest_data():
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="BAAI/bge-small-en-v1.5"
    )
    
    collection = chroma_client.get_or_create_collection(
        name="eip_data",
        embedding_function=ef
    )
    
    data_dir = "./data"
    documents = []
    ids = []
    metadatas = []
    
    bm25_corpus = []
    bm25_doc_map = []

    if not os.path.exists(data_dir):
        print(f"Directory {data_dir} does not exist. Run fetch_docs.py first.")
        return

    eip_dependency_graph = {}

    print("Processing files...")
    for filename in os.listdir(data_dir):
        if filename.endswith(".md"):
            file_path = os.path.join(data_dir, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            
            frontmatter = extract_frontmatter(text)
            title = frontmatter.get('title', 'Unknown Title')
            status = frontmatter.get('status', 'Unknown')
            requires = str(frontmatter.get('requires', ''))
            
            eip_num_match = re.search(r'eip-(\d+)', filename)
            if eip_num_match:
                eip_num = eip_num_match.group(1)
                eip_dependency_graph[eip_num] = requires

            chunks = split_by_sections(text)
            for i, chunk in enumerate(chunks):
                documents.append(chunk)
                ids.append(f"{filename}-{i}")
                
                # extract section name from chunk
                section_match = re.match(r'^## (.+)', chunk)
                section_name = section_match.group(1) if section_match else "Header"
                
                meta = {
                    "source": filename, 
                    "chunk_index": i,
                    "title": title,
                    "section": section_name,
                    "status": status,
                    "requires": requires
                }
                metadatas.append(meta)

                bm25_corpus.append(re.findall(r'\w+', chunk.lower()))
                bm25_doc_map.append({"id": f"{filename}-{i}", "content": chunk, "metadata": meta})

    if documents:
        print(f"Upserting {len(documents)} chunks into ChromaDB (in batches)...")
        batch_size = 2000
        for i in range(0, len(documents), batch_size):
            batch_end = min(i + batch_size, len(documents))
            print(f"Upserting batch {i} to {batch_end}...")
            collection.upsert(
                documents=documents[i:batch_end],
                ids=ids[i:batch_end],
                metadatas=metadatas[i:batch_end]
            )
        print("Vector upsert complete.")
        

        print("Building BM25 Index...")
        bm25 = BM25Okapi(bm25_corpus)
        
        with open("bm25_index.pkl", "wb") as f:
            pickle.dump({"model": bm25, "doc_map": bm25_doc_map, "graph": eip_dependency_graph}, f)
        print("BM25 Index and Dependency Graph saved.")
        
    else:
        print("No documents found to ingest.")

if __name__ == "__main__":
    ingest_data()
