# RavenDB AI Helpdesk - Project Status & Documentation

**Team:** Ron Blanky, Yuval Hasin, Idan Dahan  
**Last Updated:** 2026-02-05

---

## 📋 Project Overview

**Goal:** Build a Telegram bot that answers questions about RavenDB based on collected data (GitHub Discussions, Google Groups, Documentation).

**End of Semester A Target:** Present an initial working solution of the Telegram bot.

---

## ✅ Completed Tasks

### Week 1-2 (Feb 2026)

| Task | Status | Notes |
|------|--------|-------|
| Created RavenDB Cloud account | ✅ | Ron's email |
| Created Cluster + Database (HelpdeskDB) | ✅ | URL: `https://a.free.helpdesk.ravendb.cloud` |
| Installed client certificate | ✅ | For secure connection |
| Cloned PropertySphere sample project | ✅ | Reference for Telegram bot implementation |
| Created data collection script | ✅ | `scripts/collect_discussions.py` |
| Collected GitHub Discussions | ✅ | **1,052 discussions** collected |
| Contacted Oren (CEO) for guidance | ✅ | Got useful feedback |

---

## 🔄 Current Status

### Oren's Feedback (Feb 5, 2026)

1. **Local vs Cloud:** Suggests using local RavenDB + developer license instead of cloud
2. **Local AI:** Can use OLLAMA or VLLM for local AI (no OpenAI needed)
3. **Cloud Credits:** Register at https://ravendb.net/promo2026 for $300 credit
4. **OpenAI Credits:** Need to get from college or use local AI
5. **Python Script:** Confirmed it's sufficient for data collection
6. **Additional Data:** Add Google Groups + official documentation
7. **Presentation Focus:** What we did, challenges, current progress

---

## 🎯 Next Steps

### Immediate (This Week)
- [x] Decide: Local RavenDB + OLLAMA vs Cloud + OpenAI → **Chose Option B!**
- [x] Register for $300 cloud credit at https://ravendb.net/promo2026 → **Got Developer License**
- [x] Create script for Google Groups data collection → `collect_google_groups.py`
- [x] Create script for RavenDB Docs collection → `collect_documentation.py`
- [x] Install RavenDB locally → **Done! http://127.0.0.1:8080** ✅
- [ ] Install OLLAMA + download model (`llama3.1:8b`)
- [ ] Add license to RavenDB
- [ ] Import collected discussions to local HelpdeskDB

### Short Term (Before Semester End)
- [ ] Set up AI Agent with local OLLAMA
- [ ] Create Telegram bot using PropertySphere as reference
- [ ] Connect bot to RavenDB AI Agent
- [ ] Test and iterate

### For Presentation
- [ ] Document what we built
- [ ] List challenges we overcame
- [ ] Show working demo

---

## 🖥️ Hardware Specifications

| Component | Specs | Notes |
|-----------|-------|-------|
| **GPU** | NVIDIA RTX 4060 | 8GB VRAM - Perfect for local AI! |
| **RAM** | 16GB DDR3 @ 1333MHz | Older but sufficient |
| **Recommended Model** | `llama3.1:8b` | Uses ~5GB VRAM, leaves room for system |

**Why RTX 4060 is great:**
- OLLAMA loads model directly to GPU VRAM (not system RAM)
- ~50x faster than CPU-only inference
- Can run professional-grade 8B parameter models
- Shows "Edge AI" capability in presentation ✨

---

## 🚧 Challenges & Solutions

| Challenge | Status | Solution |
|-----------|--------|----------|
| AI Agents not available in Free tier | ✅ Solved | Using Local RavenDB + Developer License |
| Need OpenAI API key | ✅ Solved | Using OLLAMA locally instead |
| Limited system RAM (2.6GB free) | ✅ Solved | RTX 4060 has 8GB VRAM for model loading |
| Google Groups data collection | 🟡 Script Ready | `collect_google_groups.py` - requires Selenium |
| Documentation collection | 🟡 Script Ready | `collect_documentation.py` created |

---

## 📁 Project Structure

```
RavenDB/
├── config/
│   └── cluster_config.env          # Cloud configuration (backup)
├── scripts/
│   ├── collect_discussions.py      # GitHub Discussions collector ✅
│   ├── collect_google_groups.py    # Google Groups collector ✅
│   └── collect_documentation.py    # RavenDB Docs collector ✅
├── samples.properties/             # Reference sample project
│   └── Services/
│       ├── PropertyAgent.cs        # AI Agent example
│       └── TelegramPollingService.cs  # Telegram bot example
└── docs/
    ├── PROJECT_STATUS.md           # This file
    └── LOCAL_SETUP_GUIDE.md        # Installation guide ✅
```

---

## 🔑 Key Resources

| Resource | URL/Path |
|----------|----------|
| **Local RavenDB** | http://127.0.0.1:8080 ✅ |
| RavenDB Download | https://ravendb.net/download |
| OLLAMA Download | https://ollama.com/download |
| PropertySphere Sample | `samples.properties/` |
| GitHub Discussions | https://github.com/ravendb/ravendb/discussions |
| Google Groups | https://groups.google.com/g/ravendb |
| RavenDB Docs | https://ravendb.net/docs |
| Setup Guide | `docs/LOCAL_SETUP_GUIDE.md` |

---

## 📊 Data Collection Stats

| Source | Count | Status |
|--------|-------|--------|
| GitHub Discussions | 1,052 | ✅ Collected |
| Google Groups | - | 🟡 Script ready, needs run |
| Documentation | - | 🟡 Script ready, needs run |

---

## 💡 Architecture Decisions

### ~~Option A: Cloud-Based~~
- ~~RavenDB Cloud + $300 credit~~
- ~~OpenAI API (need credits from college)~~

### ✅ Option B: Local-Based (CHOSEN - Oren's Suggestion)
- Local RavenDB + Developer License (Ruppin)
- OLLAMA for local AI with RTX 4060 GPU
- **Model:** `llama3.1:8b` (8 billion parameters)
- **Pros:** Full control, no external dependencies, free, fast GPU inference!
- **Cons:** Initial setup complexity (now done ✅)

**Decision:** Option B - Local RavenDB + OLLAMA ✅

---

## 🤖 AI Model Selection

### Why `llama3.1:8b`?

| Factor | llama3.1:8b | gemma2:9b | qwen2.5:7b |
|--------|-------------|-----------|------------|
| **Context Window** | **128K** ✅ | 8K ❌ | 128K ✅ |
| **VRAM Usage** | ~5GB ✅ | ~6GB ⚠️ | ~4.5GB ✅ |
| **Code Generation** | Good | Good | Best |
| **NLP/Explanation** | **Best** ✅ | Good | Fair |

### Decision Rationale

1. **Context Window is Critical**: For RAG (Retrieval Augmented Generation), the model must read multiple documents at once. Gemma 2's 8K limit would cut off important information.

2. **Helpdesk = Explanation + Some Code**: Our users are developers asking RavenDB questions. They need clear explanations with occasional code snippets (RQL, C#). Llama 3.1 excels at this balance.

3. **Hardware Fit**: 
   - RTX 4060 = 8GB VRAM
   - Model uses ~5GB → leaves room for Windows (~2-3GB)
   - 100% GPU execution = no DDR3 RAM bottleneck

4. **Industry Standard**: Llama 3.1 is the go-to model for local RAG systems in 2025/2026.

### Alternative Considered
- **Qwen 2.5 7B**: Better at code, but Llama's superior natural language explanations are more valuable for Helpdesk use case.

---

## 📝 Meeting Notes / Updates

### Feb 10, 2026 (Update 6) - Data Ingestion Complete 📥
- **Milestone Reached**: Successfully imported **1,052 GitHub Discussions** into `HelpdeskDB`.
- **Status**: License (Ruppin) is active, OLLAMA connection is confirmed.
- **Next Step**: Finalize AI Agent configuration and Knowledge Base (RAG).

### Feb 5, 2026 (Update 4) - Model Selection
- **Evaluated 4 models**: Llama 3.1 8B, Gemma 2 9B, Qwen 2.5 7B, Mistral 7B
- **Key insight**: Context window (128K) critical for RAG - eliminates Gemma 2
- **Decision**: `llama3.1:8b` - best balance of explanation quality + code + hardware fit
- **Why not larger models**: 13B+ would overflow 8GB VRAM → fall back to slow DDR3 RAM

### Feb 5, 2026 (Update 3)
- ✅ **RavenDB installed successfully!** Available at http://127.0.0.1:8080
- Configuration: Unsecure mode, Node A, Port 8080
- Discovered Ron has **RTX 4060 GPU** - game changer for AI!
- Updated model recommendation: `llama3.1:8b` (runs on GPU VRAM)
- **Next:** Install OLLAMA, download model, add license

### Feb 5, 2026 (Update 2)
- **Decided to go with Option B** (Local RavenDB + OLLAMA)
- Received Developer License from Oren (Name: "Ruppin")
- Created installation guide: `docs/LOCAL_SETUP_GUIDE.md`
- Created Google Groups script: `scripts/collect_google_groups.py`
- Created Documentation script: `scripts/collect_documentation.py`

### Feb 5, 2026
- Received feedback from Oren
- Need to decide between local and cloud approach
- Created this documentation file

### Feb 3, 2026
- Successfully collected 1,052 GitHub discussions
- Discovered AI Agents require Production license
- Sent email to Oren requesting help

---

## 🎓 For Presentation (Oren's Requirements)

### What We Did
1. Set up RavenDB Cloud → discovered Free tier limitations → pivoted to local
2. Collected 1,052 GitHub Discussions using Python script
3. Installed local RavenDB with Developer License
4. Selected optimal AI model based on hardware analysis

### Challenges Overcome
1. **Free tier doesn't include AI Agents** → Solution: Local RavenDB + Dev License
2. **No OpenAI API key** → Solution: OLLAMA (free, local)
3. **Limited system RAM (2.6GB free)** → Solution: RTX 4060 GPU with 8GB VRAM
4. **Model selection complexity** → Solution: Analyzed context window, VRAM, use case

### Current Progress
- ✅ RavenDB local server running
- ✅ 1,052 discussions collected
- ✅ Data collection scripts ready
- 🔄 Next: OLLAMA + Telegram bot

---

*This document follows the Architected Vibing methodology - updated after each significant milestone.*


