import requests
import os
import re

def fetch_all_eips():

    api_url = "https://api.github.com/repos/ethereum/ERCs/contents/ERCS"
    data_dir = "./data"
    os.makedirs(data_dir, exist_ok=True)
    
    print("Fetching ERC list from GitHub...")
    try:
        response = requests.get(api_url)
        response.raise_for_status()
        files = response.json()
        
        count = 0
        limit = 500
        
        for file in files:
            if count >= limit:
                break
            
            name = file['name']
            download_url = file['download_url']
            
            if name.endswith(".md"):
                try:

                    res = requests.get(download_url)
                    content = res.text
                    

                    with open(os.path.join(data_dir, name), "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    print(f"Saved {name}")
                    count += 1
                except Exception as e:
                    print(f"Failed to download {name}: {e}")
        
        print(f"Successfully downloaded {count} EIPs.")
            
    except Exception as e:
        print(f"Error fetching EIP list: {e}")

if __name__ == "__main__":
    fetch_all_eips()
