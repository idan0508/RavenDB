"""
Import GitHub Discussions into RavenDB
ייבוא הדיונים מגיטהאב לRavenDB

Run this:
python import_to_ravendb.py
"""

import json
import requests
from datetime import datetime

# RavenDB Configuration
RAVENDB_URL = "http://127.0.0.1:8080"
DATABASE_NAME = "HelpdeskDB"

# Disable compression issues
session = requests.Session()
session.headers.update({
    'Accept-Encoding': 'identity',
    'Content-Type': 'application/json'
})

def import_discussions():
    """Import all 1,052 discussions into RavenDB"""
    
    discussions_file = "collected_discussions/discussions_latest.json"
    print(f"Loading {discussions_file}...")
    
    with open(discussions_file, 'r', encoding='utf-8') as f:
        discussions = json.load(f)
    
    print(f"Found {len(discussions)} discussions")
    print("Importing to RavenDB...")
    
    imported = 0
    failed = 0
    
    for i, disc in enumerate(discussions):
        doc_id = f"discussions/{disc['Number']}"
        
        try:
            response = session.put(
                f"{RAVENDB_URL}/databases/{DATABASE_NAME}/docs?id={doc_id}",
                json=disc
            )
            if response.status_code in [200, 201, 204]:
                imported += 1
            else:
                failed += 1
        except:
            failed += 1
        
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(discussions)}...")
    
    print(f"\n✅ Done! Imported: {imported}, Failed: {failed}")

if __name__ == "__main__":
    print("="*50)
    print("RavenDB Helpdesk - Import Script")
    print("="*50)
    print("\nMake sure:")
    print("1. RavenDB is running (http://127.0.0.1:8080)")
    print("2. Database 'HelpdeskDB' exists")
    print()
    input("Press Enter to start...")
    import_discussions()
    print("\nDone! Now configure AI Connection String in Studio.")
