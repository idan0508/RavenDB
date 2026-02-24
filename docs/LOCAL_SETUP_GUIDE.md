# Local Installation Guide - RavenDB + OLLAMA

**Updated:** 2026-02-05

---

## 📋 Current Status

| Component | Status | Details |
|-----------|--------|---------|
| **RavenDB** | ✅ Installed | Running at `http://127.0.0.1:8080` (or dynamic port) |
| **OLLAMA** | ✅ Installed | App running |
| **AI Model** | ✅ Configured | `llama3.1:8b` (Correct model for RTX 4060) |
| **License** | ✅ Applied | **Developer License** (Ruppin) - AI features UNLOCKED |
| **Data** | ✅ Ingested | 1,052 GitHub Discussions in `HelpdeskDB` |

---

## 🚨 NEXT STEP: Download Correct Model

**Problem:** You have `gemma3:4b` but need `llama3.1:8b` for better performance.

### Open PowerShell and run:
```powershell
ollama pull llama3.1:8b
```

This will download ~5GB. Wait for it to finish.

### Then test it:
```powershell
ollama run llama3.1:8b
```

Type a question like "What is RavenDB?" and watch Task Manager → GPU to see VRAM usage jump to ~5GB.

---

## Step 1: RavenDB Installation ✅ DONE

Your RavenDB is installed at:
```
C:\Users\Ron\Downloads\RavenDB-7.2.0-windows-x64
```

To start RavenDB:
```powershell
cd C:\Users\Ron\Downloads\RavenDB-7.2.0-windows-x64
.\run.ps1
```

Studio URL: **http://127.0.0.1:52824**

---

## Step 2: Add License to RavenDB

1. Open RavenDB Studio: http://127.0.0.1:52824
2. Go to: **Settings** → **License** (in left sidebar)
3. Click **Activate** or **Register**
4. Paste this JSON:

```json
{
    "Id": "67905d74-6942-409a-832d-e6fef909e536",
    "Name": "Ruppin",
    "Keys": [
        "qanxtbn4Qx3nAl0Q5o231/WwZ",
        "xzpTX+2HI+P7WIvj/qZxPMmuU",
        "sBcOg4kpMfMA7iXyK4zPfziwM",
        "ufst6NlCEWe6/bTHjNd2UclNE",
        "edjKvsIEjsB+Ug9NsN5fg6rtx",
        "QbABb596IPQ2kz91grU6lswld",
        "zUHLG7hs6zHE3sqhfxct1ABYE",
        "DNy4yBSYoSQMqKywtLi8wJzEy",
        "MzQVFjc4OTo7PD0+nwlffJ8Cf",
        "CCfAiEgnwljU8CJCCfAiUgnw",
        "ImlJ8CJyCfAiggnwlpIJ8CKiC",
        "fAisgnwIsIJ8CLSCfAi4gnwIv",
        "IJ8CMCCfAzZAAZ8CQiCfAkMgn",
        "wJEIJ8CRSCfAkYgnwJHIJ8CSC",
        "BDJEQJYgZdnwRBYANd"
    ]
}
```

5. Click **Save** or **Activate**

---

## Step 3: OLLAMA Installation ✅ DONE

OLLAMA is installed and running.

### Change the model in OLLAMA UI:
1. Click on `gemma3:4b` dropdown (bottom right)
2. Search for `llama3.1:8b`
3. If not found, run in PowerShell: `ollama pull llama3.1:8b`

---

## Step 4: Connect RavenDB to OLLAMA

1. Open RavenDB Studio: http://127.0.0.1:52824
2. Go to: **AI Hub** → **AI Connection Strings**
3. Click **Add new connection string**
4. Configure:

| Setting | Value |
|---------|-------|
| Name | `Local-Ollama` |
| Model Type | Chat |
| Connector | Ollama |
| Ollama URI | `http://localhost:11434` |
| Model | `llama3.1:8b` |

5. Click **Save**

---

## Step 5: Create Database

1. Go to: **Databases** → **New database**
2. Name: `HelpdeskDB`
3. Click **Create**

---

## Step 6: Create AI Agent

1. Go to: **AI Hub** → **AI Agents**
2. Click **Add new agent**
3. Configure:

| Setting | Value |
|---------|-------|
| Name | `RavenDB-Helpdesk` |
| Connection String | `Local-Ollama` |
| System Prompt | See below |

**System Prompt:**
```
You are a RavenDB support assistant. Answer questions about RavenDB based on the documentation and discussions provided. Be helpful, accurate, and provide code examples in RQL or C# when relevant.
```

---

## 🎯 Hardware Configuration

| Component | Your Specs | Requirement |
|-----------|------------|-------------|
| GPU | RTX 4060 (8GB VRAM) ✅ | 6GB+ VRAM |
| Model | llama3.1:8b | ~5GB VRAM |
| Free VRAM | ~3GB for Windows | ✅ Good |

---

## 📋 Quick Commands Reference

```powershell
# Start RavenDB
cd C:\Users\Ron\Downloads\RavenDB-7.2.0-windows-x64
.\run.ps1

# Pull correct model
ollama pull llama3.1:8b

# Run model (interactive test)
ollama run llama3.1:8b

# List installed models
ollama list

# Check OLLAMA service
ollama serve
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| RavenDB port changed | Normal - it uses an available port |
| OLLAMA shows wrong model | Run `ollama pull llama3.1:8b` then select it |
| Connection refused | Make sure OLLAMA is running (`ollama serve`) |
| GPU not being used | Check NVIDIA drivers are up to date |

---

## ✅ Checklist

- [x] RavenDB installed
- [x] RavenDB running
- [x] OLLAMA installed
- [x] Download `llama3.1:8b` model
- [x] Add Ruppin license to RavenDB
- [x] Create HelpdeskDB database
- [x] Connect RavenDB to OLLAMA
- [ ] Create AI Agent
- [ ] Configure Knowledge Base (RAG)
