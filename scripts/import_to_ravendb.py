"""
Import Data into RavenDB (Multi-Source, with Deduplication)
===========================================================
Imports discussions, documentation, and Google Groups data into RavenDB.

Supports multiple data sources:
  - GitHub Discussions     → "Discussions" collection
  - Google Groups          → "GoogleGroupsDiscussions" collection
  - RavenDB Documentation  → "Documentation" collection

Usage:
    python import_to_ravendb.py                          # Import all latest files
    python import_to_ravendb.py --source discussions      # Import only discussions
    python import_to_ravendb.py --source google_groups    # Import only Google Groups
    python import_to_ravendb.py --source documentation    # Import only documentation

Author: Ron Blanky, Idan Dahan
Project: RavenDB AI Helpdesk - Final Year Project
"""

import json
import os
import argparse
import requests
from datetime import datetime

# ====== CONFIGURATION ======
RAVENDB_URL = "http://127.0.0.1:8080"
DATABASE_NAME = "HelpdeskDB"
INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "collected_discussions")

# Source configurations: (file_pattern, collection, id_field)
SOURCES = {
    "discussions": {
        "file": "discussions_latest.json",
        "collection": "Discussions",
        "id_func": lambda doc: f"discussions/{doc.get('Number', 'unknown')}",
        "dedup_field": "UpdatedAt",
    },
    "google_groups": {
        "file": "google_groups_latest.json",
        "collection": "GoogleGroupsDiscussions",
        "id_func": lambda doc: f"google-groups/{_url_to_id(doc.get('Url', ''))}",
        "dedup_field": None,  # Always overwrite
    },
    "documentation": {
        "file": "documentation_latest.json",
        "collection": "Documentation",
        "id_func": lambda doc: f"docs/{doc.get('Version', '0')}/{_url_to_id(doc.get('Url', ''))}",
        "dedup_field": None,  # Always overwrite
    },
}

# Setup session
session = requests.Session()
session.headers.update({
    'Accept-Encoding': 'identity',
    'Content-Type': 'application/json'
})


def _url_to_id(url: str) -> str:
    """Convert a URL to a safe document ID component."""
    if not url:
        return "unknown"
    # Take the path portion and clean it
    from urllib.parse import urlparse
    path = urlparse(url).path
    # Remove leading slash and replace slashes with dashes
    clean = path.strip('/').replace('/', '-').replace('.', '-')
    # Limit length
    return clean[:200] if clean else "unknown"


def get_existing_doc(doc_id: str) -> dict | None:
    """Check if a document already exists in RavenDB."""
    try:
        response = session.get(
            f"{RAVENDB_URL}/databases/{DATABASE_NAME}/docs?id={doc_id}"
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("Results") and len(data["Results"]) > 0:
                return data["Results"][0]
    except Exception:
        pass
    return None


def import_source(source_name: str, source_config: dict) -> dict:
    """Import a single data source into RavenDB."""
    filepath = os.path.join(INPUT_DIR, source_config["file"])

    if not os.path.exists(filepath):
        print(f"   ⚠️ File not found: {filepath}")
        return {"imported": 0, "skipped": 0, "failed": 0, "total": 0}

    print(f"   📄 Loading {filepath}...")

    with open(filepath, 'r', encoding='utf-8') as f:
        documents = json.load(f)

    total = len(documents)
    print(f"   📊 Found {total} documents")

    imported = 0
    skipped = 0
    failed = 0

    for i, doc in enumerate(documents):
        doc_id = source_config["id_func"](doc)

        # Deduplication check
        dedup_field = source_config.get("dedup_field")
        if dedup_field:
            existing = get_existing_doc(doc_id)
            if existing:
                existing_val = existing.get(dedup_field, "")
                new_val = doc.get(dedup_field, "")
                if existing_val and existing_val == new_val:
                    skipped += 1
                    if (i + 1) % 100 == 0:
                        print(f"      {i+1}/{total}... (imported: {imported}, skipped: {skipped})")
                    continue

        # Ensure metadata is set
        if "@metadata" not in doc:
            doc["@metadata"] = {}
        doc["@metadata"]["@collection"] = source_config["collection"]

        # Import
        try:
            response = session.put(
                f"{RAVENDB_URL}/databases/{DATABASE_NAME}/docs?id={doc_id}",
                json=doc
            )
            if response.status_code in [200, 201, 204]:
                imported += 1
            else:
                failed += 1
        except Exception:
            failed += 1

        if (i + 1) % 100 == 0:
            print(f"      {i+1}/{total}... (imported: {imported})")

    return {"imported": imported, "skipped": skipped, "failed": failed, "total": total}


def main():
    parser = argparse.ArgumentParser(description='Import data into RavenDB')
    parser.add_argument(
        '--source', choices=['discussions', 'google_groups', 'documentation', 'all'],
        default='all',
        help='Which data source to import (default: all)'
    )
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 RavenDB Helpdesk — Multi-Source Import")
    print("=" * 60)
    print(f"RavenDB: {RAVENDB_URL}")
    print(f"Database: {DATABASE_NAME}")
    print()

    # Check RavenDB connectivity
    try:
        r = session.get(f"{RAVENDB_URL}/databases/{DATABASE_NAME}/stats")
        if r.status_code == 200:
            stats = r.json()
            print(f"✅ Connected! Current docs: {stats.get('CountOfDocuments', '?')}")
        else:
            print(f"⚠️ RavenDB responded with status {r.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to RavenDB: {e}")
        print(f"   Make sure RavenDB is running at {RAVENDB_URL}")
        return

    print()

    # Determine sources to import
    if args.source == 'all':
        sources_to_import = list(SOURCES.keys())
    else:
        sources_to_import = [args.source]

    # Import each source
    all_stats = {}
    for source_name in sources_to_import:
        config = SOURCES[source_name]
        print(f"📦 Importing: {source_name} → {config['collection']}")
        stats = import_source(source_name, config)
        all_stats[source_name] = stats
        print(f"   ✅ Imported: {stats['imported']}, "
              f"Skipped: {stats['skipped']}, "
              f"Failed: {stats['failed']}")
        print()

    # Final summary
    print("=" * 60)
    print("📊 Import Summary")
    print("=" * 60)
    total_imported = 0
    total_skipped = 0
    for source, stats in all_stats.items():
        print(f"   {source:20s}: {stats['imported']:4d} imported, "
              f"{stats['skipped']:4d} skipped, {stats['failed']:4d} failed "
              f"(of {stats['total']})")
        total_imported += stats['imported']
        total_skipped += stats['skipped']
    print(f"   {'─' * 50}")
    print(f"   {'TOTAL':20s}: {total_imported:4d} imported, {total_skipped:4d} skipped")
    print("=" * 60)


if __name__ == "__main__":
    print()
    print("Make sure:")
    print(f"1. RavenDB is running ({RAVENDB_URL})")
    print(f"2. Database '{DATABASE_NAME}' exists")
    print()
    input("Press Enter to start...")
    main()
    print("\n✅ Done!")
