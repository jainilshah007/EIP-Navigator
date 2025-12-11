import chromadb
from chromadb.utils import embedding_functions
from agents import LibrarianAgent
import time

def evaluate_retrieval():
    print("Initializing Agent...")
    librarian = LibrarianAgent()
    
    test_cases = [
        ("ERC-20 Token Standard", "eip-20.md"),
        ("Non-Fungible Token NFT", "eip-721.md"),
        ("Tokenized Vault Standard", "eip-4626.md"),
        ("EIP-1 definition", "eip-1.md"),
        ("Hardfork Meta", "eip-1.md")
    ]
    
    hits = 0
    total = len(test_cases)
    start_time = time.time()
    
    print(f"\nRunning Evaluation on {total} queries...\n")
    print(f"{'Query':<30} | {'Expected':<15} | {'Rank found':<10} | {'Status'}")
    print("-" * 70)
    
    for query, expected_eip in test_cases:
        results = librarian.retrieve(query, n_results=5)
        found_rank = -1
        
        for rank, doc in enumerate(results):
            content = doc['content']
            num = expected_eip.split('.')[0].split('-')[1]
            if f"eip-{num}" in content.lower() or f"erc-{num}" in content.lower() or expected_eip in content:  
                 found_rank = rank + 1
                 break
        
        status = "HIT" if found_rank > 0 else "MISS"
        if found_rank > 0:
            hits += 1
            
        print(f"{query[:28]:<30} | {expected_eip:<15} | {found_rank if found_rank > 0 else '-':<10} | {status}")

    end_time = time.time()
    recall_at_5 = hits / total
    
    print("\n" + "="*30)
    print(f"Recall@5: {recall_at_5 * 100:.1f}%")
    print(f"Latency: {(end_time - start_time):.2f}s")
    print("="*30)
    
    if recall_at_5 < 0.5:
        print("[!] Low Recall. Consider adjusting BM25 weights or chunking.")
    else:
        print("[*] Good Retrieval Performance.")

if __name__ == "__main__":
    evaluate_retrieval()
