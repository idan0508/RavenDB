"""
GitHub Discussions Collector for RavenDB Helpdesk Project
==========================================================
This script collects ALL discussions from the ravendb/ravendb repository
and saves them to RavenDB for use with the AI Agent.

Requirements:
    pip install requests

Usage:
    1. Set environment variable: $env:GITHUB_TOKEN = "your_token_here"
    2. Run: python collect_discussions.py

Author: Ron Blanky, Idan Dahan
Project: RavenDB AI Helpdesk - Final Year Project
"""

import os
import json
import time
import requests
from datetime import datetime
from typing import Optional, Generator

# ====== CONFIGURATION ======
# Try to read .env file manually
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OWNER = "ravendb"
REPO = "ravendb"
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "collected_discussions")
GRAPHQL_URL = "https://api.github.com/graphql"

# ====== GraphQL Query ======
DISCUSSIONS_QUERY = """
query($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    discussions(first: 100, after: $cursor) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        id
        number
        title
        body
        createdAt
        updatedAt
        url
        upvoteCount
        isAnswered
        category {
          name
          emoji
          description
        }
        author {
          login
        }
        labels(first: 10) {
          nodes {
            name
          }
        }
        comments(first: 50) {
          totalCount
          nodes {
            body
            createdAt
            author {
              login
            }
            isAnswer
          }
        }
        answer {
          body
          createdAt
          author {
            login
          }
        }
      }
    }
  }
}
"""

def get_headers() -> dict:
    """Create request headers with authentication."""
    if not GITHUB_TOKEN:
        print("⚠️  Warning: GITHUB_TOKEN not set. Rate limits will be very low.")
        print("   Set it with: $env:GITHUB_TOKEN = 'your_token'")
        return {"Content-Type": "application/json"}
    
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json"
    }

def fetch_discussions_page(cursor: Optional[str] = None) -> dict:
    """Fetch a single page of discussions."""
    variables = {
        "owner": OWNER,
        "repo": REPO,
        "cursor": cursor
    }
    
    response = requests.post(
        GRAPHQL_URL,
        headers=get_headers(),
        json={"query": DISCUSSIONS_QUERY, "variables": variables}
    )
    
    if response.status_code != 200:
        raise Exception(f"GitHub API error: {response.status_code} - {response.text}")
    
    data = response.json()
    
    if "errors" in data:
        raise Exception(f"GraphQL errors: {data['errors']}")
    
    return data

def fetch_all_discussions() -> Generator[dict, None, None]:
    """Generator that yields all discussions with pagination."""
    cursor = None
    page = 1
    
    while True:
        print(f"📄 Fetching page {page}...", end=" ", flush=True)
        
        try:
            data = fetch_discussions_page(cursor)
        except Exception as e:
            print(f"❌ Error: {e}")
            # Wait and retry on rate limit
            if "rate limit" in str(e).lower():
                print("⏳ Rate limited. Waiting 60 seconds...")
                time.sleep(60)
                continue
            raise
        
        discussions = data["data"]["repository"]["discussions"]
        page_info = discussions["pageInfo"]
        nodes = discussions["nodes"]
        
        print(f"Got {len(nodes)} discussions")
        
        for discussion in nodes:
            yield discussion
        
        if not page_info["hasNextPage"]:
            print("✅ Reached last page!")
            break
        
        cursor = page_info["endCursor"]
        page += 1
        
        # Respect rate limits
        time.sleep(0.5)

def transform_discussion(discussion: dict) -> dict:
    """Transform GitHub discussion to RavenDB document format."""
    
    # Extract labels
    labels = [label["name"] for label in discussion.get("labels", {}).get("nodes", [])]
    
    # Extract comments
    comments = []
    for comment in discussion.get("comments", {}).get("nodes", []):
        comments.append({
            "Body": comment.get("body", ""),
            "Author": comment.get("author", {}).get("login", "unknown"),
            "CreatedAt": comment.get("createdAt"),
            "IsAnswer": comment.get("isAnswer", False)
        })
    
    # Extract answer if exists
    answer = None
    if discussion.get("answer"):
        answer = {
            "Body": discussion["answer"].get("body", ""),
            "Author": discussion["answer"].get("author", {}).get("login", "unknown"),
            "CreatedAt": discussion["answer"].get("createdAt")
        }
    
    # Create the document
    return {
        # RavenDB will auto-generate ID, but we can suggest one
        "@metadata": {
            "@collection": "Discussions"
        },
        "GitHubId": discussion.get("id"),
        "Number": discussion.get("number"),
        "Title": discussion.get("title", ""),
        "Body": discussion.get("body", ""),
        "Url": discussion.get("url", ""),
        "CreatedAt": discussion.get("createdAt"),
        "UpdatedAt": discussion.get("updatedAt"),
        "Author": discussion.get("author", {}).get("login", "unknown"),
        "Category": {
            "Name": discussion.get("category", {}).get("name", ""),
            "Emoji": discussion.get("category", {}).get("emoji", ""),
            "Description": discussion.get("category", {}).get("description", "")
        },
        "Labels": labels,
        "UpvoteCount": discussion.get("upvoteCount", 0),
        "IsAnswered": discussion.get("isAnswered", False),
        "CommentsCount": discussion.get("comments", {}).get("totalCount", 0),
        "Comments": comments,
        "Answer": answer,
        # Combined text for Vector Search
        "SearchableContent": f"{discussion.get('title', '')} {discussion.get('body', '')}"
    }

def save_to_json(discussions: list, filename: str):
    """Save discussions to JSON file for later import."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(discussions, f, indent=2, ensure_ascii=False)
    
    print(f"💾 Saved to {filepath}")

def main():
    print("=" * 60)
    print("🚀 RavenDB GitHub Discussions Collector")
    print("=" * 60)
    print(f"Repository: {OWNER}/{REPO}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    # Check token
    if not GITHUB_TOKEN:
        print("⚠️  No GITHUB_TOKEN found!")
        print("   Please set it: $env:GITHUB_TOKEN = 'ghp_your_token_here'")
        print("   Get a token from: https://github.com/settings/tokens")
        print()
        response = input("Continue without token? (rate limits apply) [y/N]: ")
        if response.lower() != 'y':
            return
    
    # Collect all discussions
    all_discussions = []
    start_time = time.time()
    
    try:
        for discussion in fetch_all_discussions():
            transformed = transform_discussion(discussion)
            all_discussions.append(transformed)
            
            # Progress indicator
            if len(all_discussions) % 100 == 0:
                print(f"   📊 Collected {len(all_discussions)} discussions so far...")
    
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted! Saving collected data...")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("   Saving collected data...")
    
    # Calculate statistics
    elapsed = time.time() - start_time
    answered = sum(1 for d in all_discussions if d.get("IsAnswered"))
    
    # Print statistics
    print()
    print("=" * 60)
    print("📊 Collection Statistics")
    print("=" * 60)
    print(f"Total discussions: {len(all_discussions)}")
    print(f"Answered: {answered} ({100*answered/max(len(all_discussions),1):.1f}%)")
    print(f"Time elapsed: {elapsed:.1f} seconds")
    print()
    
    # Save to JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_to_json(all_discussions, f"discussions_{timestamp}.json")
    save_to_json(all_discussions, "discussions_latest.json")
    
    # Print category breakdown
    categories = {}
    for d in all_discussions:
        cat = d.get("Category", {}).get("Name", "Unknown")
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n📁 Categories breakdown:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"   {cat}: {count}")
    
    print("\n" + "=" * 60)
    print("✅ Done! Next steps:")
    print("   1. Start RavenDB: cd C:\\RavenDB && .\\run.ps1")
    print("   2. Import to RavenDB Studio: Databases → HelpdeskDB → Import Data")
    print("   3. Choose the JSON file from collected_discussions/")
    print("=" * 60)

if __name__ == "__main__":
    main()
