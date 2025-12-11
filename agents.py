import os
import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI
from dotenv import load_dotenv
import pickle
import json
import re

load_dotenv()

class LibrarianAgent:
    def __init__(self):
        self.chroma_client = chromadb.PersistentClient(path="./chroma_db")
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-small-en-v1.5"
        )
        self.collection = self.chroma_client.get_collection(
            name="eip_data",
            embedding_function=self.ef
        )
        # load bm25 index
        try:
            with open("bm25_index.pkl", "rb") as f:
                data = pickle.load(f)
                self.bm25 = data["model"]
                self.bm25_map = data["doc_map"]
                self.graph = data["graph"]
        except FileNotFoundError:
            print("Warning: bm25_index.pkl not found. Run ingest.py first.")
            self.bm25 = None
            self.graph = {}

    def retrieve(self, query: str, n_results: int = 5):
        unique_docs = {}
        
        # if query has explicit ERC number, inject matching docs directly
        eip_matches = re.findall(r'(?:eip|erc)[-\s]?(\d+)', query.lower())
        if eip_matches and self.bm25_map:
            for num in eip_matches:
                for doc_item in self.bm25_map:
                    source = doc_item['metadata'].get('source', '').lower()
                    if source == f"erc-{num}.md" or source == f"eip-{num}.md":
                        doc_id = doc_item['id']
                        if doc_id not in unique_docs:
                            unique_docs[doc_id] = {
                                "content": doc_item['content'],
                                "metadata": doc_item['metadata'],
                                "score": 10.0
                            }
        
        # vector search
        try:
            vector_results = self.collection.query(
                query_texts=[query],
                n_results=n_results * 2
            )
            
            if vector_results['documents']:
                for i, doc in enumerate(vector_results['documents'][0]):
                    doc_id = vector_results['ids'][0][i]
                    unique_docs[doc_id] = {
                        "content": doc,
                        "metadata": vector_results['metadatas'][0][i],
                        "score": 1.0 / (i + 1)
                    }
        except Exception as e:
            print(f"Vector search failed: {e}")

        # bm25 keyword search
        if self.bm25:
            tokenized_query = query.lower().split(" ")
            bm25_scores = self.bm25.get_scores(tokenized_query)
            top_n = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:n_results * 2]
            
            for rank, idx in enumerate(top_n):
                doc_item = self.bm25_map[idx]
                doc_id = doc_item['id']
                rrf_score = 1.0 / (rank + 1)
                
                if doc_id in unique_docs:
                    unique_docs[doc_id]['score'] += rrf_score
                else:
                    unique_docs[doc_id] = {
                        "content": doc_item['content'],
                        "metadata": doc_item['metadata'],
                        "score": rrf_score
                    }

        # boost exact matches
        eip_matches = re.findall(r'(?:eip|erc)[-\s]?(\d+)', query.lower())
        if eip_matches:
            for doc_id, doc_data in unique_docs.items():
                source = doc_data['metadata'].get('source', '').lower()
                title = doc_data['metadata'].get('title', '').lower()
                
                for num in eip_matches:
                    if f"erc-{num}.md" == source or f"eip-{num}.md" == source:
                        doc_data['score'] *= 5.0
                        break

                    elif f"erc {num}" in title or f"eip {num}" in title:
                        doc_data['score'] *= 2.0
                        break

        # sort and limit
        sorted_docs = sorted(unique_docs.values(), key=lambda x: x['score'], reverse=True)[:n_results]
        
        # add dependency context
        expanded_context = []
        for doc in sorted_docs:
            expanded_context.append({
                "content": doc['content'],
                "metadata": doc['metadata']
            })
            
            reqs = doc['metadata'].get('requires')
            if reqs:
                expanded_context.append({
                    "content": f"\n[System Note]: The above EIP depends on EIPs: {reqs}. Consider their rules as well.\n",
                    "metadata": {"source": "System", "title": f"Dependency Graph ({reqs})"}
                })
                
        return expanded_context

class SecurityAuditorAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def audit(self, code: str):
        system_prompt = (
            "You are a Senior Smart Contract Auditor. Analyze the provided Solidity code for security vulnerabilities "
            "(re-entrancy, overflow, access control, logic errors). "
            "Return JSON format: {'status': 'PASS' or 'FAIL', 'feedback': 'string explaining issues'}."
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": code}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"status": "FAIL", "feedback": f"Audit failed: {str(e)}"}

class InterfaceEngineerAgent:
    def __init__(self):
        self.qwerty_bridge_signal = True 
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)

    def generate(self, query: str, context_list):

        context_str = "\n\n---\n\n".join([doc['content'] for doc in context_list])
        
        system_prompt = (
            "You are a Senior Solidity Security Engineer. "
            "Based ONLY on the context, provide a secure Solidity Interface/Contract. "
            "Respond with ONLY the code block if possible, or very minimal explanation."
        )
        
        user_prompt = f"Query: {query}\n\nContext:\n{context_str}"
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content

    def refine(self, original_code: str, feedback: str):
        system_prompt = "You are a Senior Solidity Engineer. Fix the code based on the Auditor's feedback."
        user_prompt = f"Original Code:\n{original_code}\n\nFeedback:\n{feedback}\n\nFix the code:"
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content

    def evaluate_precision(self, query: str, context_list):
        """Uses LLM to judge retrieval relevance."""

        context_str = "\n---\n".join([f"Chunk {i+1}: {doc['content']}..." for i, doc in enumerate(context_list)])
        
        system_prompt = (
            "You are a Search Relevance Evaluator. "
            "For each chunk, determine if it is RELEVANT to the query. "
            "Return JSON: {'relevant_count': int, 'total_count': int, 'precision': float}."
        )
        
        user_prompt = f"Query: {query}\n\nContexts:\n{context_str}"
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception:
            return {"precision": 0.0, "error": "Evaluation failed"}
