# 📖 How We Built It: RavenDB AI Helpdesk
**Project Documentation & Technical Guide**

---

## 🚀 The Mission
Build a Telegram bot that answers technical questions about RavenDB using a local AI model (RAG), avoiding cloud costs and utilizing local hardware (RTX 4060).

---

## 🛠️ Step 1: Architecture Decisions

### Why Local?
- **Privacy & Cost:** Cloud tiers for AI are expensive.
- **Hardware:** We utilized the existing **NVIDIA RTX 4060 (8GB VRAM)**.
- **Model:** Selected **`llama3.1:8b`** because:
    - It fits in 8GB VRAM (uses ~5GB).
    - It has a large context window (128K) for reading many documents.

---

## 🛠️ Step 2: Data Collection (The Knowledge Base)

We needed data to "feed" the AI.
- **Source:** GitHub Discussions (Official RavenDB repo).
- **Tool:** Python script (`scripts/collect_discussions.py`).
- **Result:** Collected **1,052 discussions** into a JSON file.
- **Challenges:** Handling pagination and API rate limits.

---

## 🛠️ Step 3: Local Infrastructure Setup

1.  **RavenDB Installation:**
    - Installed RavenDB 7.2.0 locally.
    - Port: `8080`.
    - Setup: Unsecure mode (for easy development).

2.  **Licensing (Critical Step):**
    - **Issue:** The free "Community" license blocks AI features.
    - **Solution:** Applied **Developer License** (Ruppin) manually via `settings.json` / Studio.
    - **Outcome:** Unlocked "AI Agent", "GenAI", and "Vector Search".

3.  **OLLAMA Setup:**
    - Installed OLLAMA for Windows.
    - Command: `ollama pull llama3.1:8b`.
    - Verification: `http://localhost:11434` confirms service is running.

---

## 🛠️ Step 4: Connecting the Pieces

1.  **RavenDB -> OLLAMA:**
    - Created an **AI Connection String** in RavenDB Studio.
    - Name: `Local-Ollama`.
    - URL: `http://localhost:11434`.

2.  **Data Ingestion (RAG):**
    - **Challenge:** A single 20MB JSON file is too big for AI to read at once.
    - **Solution:** Created `scripts/import_to_ravendb.py`.
    - **Process:** The script split the JSON into **1,052 separate documents** in the `Discussions` collection.
    - **Result:** Efficient Retrieval-Augmented Generation (AI reads only relevant docs).

---

## 🛠️ Step 5: Configuring the AI Agent (Current Status)

We are currently configuring the brain of the system:
1.  **Agent Name:** `RavenDB-Helpdesk`.
2.  **System Prompt:** Defined a strict persona ("RavenDB Expert Support Assistant").
3.  **Next Steps:**
    - Define the **Knowledge Base (RAG)** tool.
    - Test the agent with real questions.

---

## 📂 File Structure & Key Scripts

- `docs/PROJECT_STATUS.md` -> High-level milestones for the presentation.
- `docs/LOCAL_SETUP_GUIDE.md` -> Quick technical checklist for restarting the environment.
- `scripts/import_to_ravendb.py` -> The logic for splitting and uploading data.
