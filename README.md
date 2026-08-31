# Intelligent RAG-Based Chatbot For MITS College Students 

# My project is smart enough to answer anything related to mits college.Useful for newly joining student who want to know about the college.

An AI-powered, RAG (Retrieval-Augmented Generation) chatbot designed to assist students of Madanapalle Institute of Technology & Science (MITS) with academic rules, campus life, administration, admissions, and other college queries.

---

## 📺 Live Demo
[MITS Chatbot on Vercel](https://intelligent-rag-based-chatbot-for-m.vercel.app)


## Features

- **Hybrid Search Engine**: Combines vector database retrieval (using Qdrant) with lexical keyword matching (BM25) to provide highly relevant context matching.
- **Generative AI Responses**: Utilizes the Google Gemini model to deliver fluent, clear, and contextual answers based solely on verified MITS documentation.
- **Secure Verification (OTP)**: A mobile OTP verification system for students to register and access personalized features.
- **Conversation History**: Auto-saves and loads session conversations locally or to PostgreSQL/SQLite, letting students pick up where they left off.
- **Automatic Reindexing**: Detects updates to source text files in the dataset folder on startup and automatically runs re-indexing. Also supports manual reindexing via API.
- **Modern UI**: A responsive, premium web interface containing smooth animations, chat bubbles, and instant visual sources/citations for every answer.
- **Rate and Request Limiting**: Per-route request throttling plus request body size limits to protect the chat, OTP, and reindex endpoints.

---

## Architecture & Tech Stack

- **Frontend**: Clean HTML5, Vanilla CSS3 (dynamic gradients, transitions), and asynchronous Javascript (ES6+).
- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python) for asynchronous high-performance API handling.
- **Large Language Model (LLM)**: [Google Gemini API](https://ai.google.dev/) for generating context-based answers.
- **Vector Database**: [Qdrant](https://qdrant.tech/) client for hosting and querying embedding vectors.
- **Information Retrieval**:
  - Dense Retrieval: Gemini text-embedding models.
  - Sparse Retrieval: BM25 (using `rank-bm25`).
- **Database**: SQLite (local) and PostgreSQL support for storing conversation histories and verified user details.
- **Containerization**: Docker & Docker Compose.

### Request Limits

The API now applies route-specific limits. The defaults are:

- `POST /api/chat`: 20 requests per minute, max 8 KB body
- `POST /api/chat-stream`: 15 requests per minute, max 8 KB body
- `POST /api/send-otp`: 5 requests per minute, max 4 KB body
- `POST /api/verify-otp`: 5 requests per minute, max 4 KB body
- `POST /api/reindex`: 2 requests per hour, max 4 KB body
- `POST /api/conversations`: 30 requests per minute, max 256 KB body

You can override these with environment variables such as `CHAT_RATE_LIMIT_REQUESTS`, `CHAT_RATE_LIMIT_WINDOW_SECONDS`, or `DEFAULT_REQUEST_BODY_LIMIT_BYTES`.

---

## Project Structure

```text
├── Server/
│   ├── main.py                # FastAPI Application entry point and API routes
│   ├── sms.py                 # Mock/Twilio OTP SMS Service
│   ├── mits_scrape.py         # Scraping utility for gathering MITS website content
│   ├── evaluate_rag.py        # RAG evaluation script
│   └── rag/
│       ├── pipeline.py        # High-level RAG Query Engine
│       ├── document_processor.py # Loads and chunks document dataset
│       ├── vector_store.py    # Interfaces with Qdrant Vector Store
│       ├── bm25_retriever.py  # Keywords search retriever
│       ├── hybrid_searcher.py # Combines Dense (Vector) + Sparse (BM25) results
│       └── generator.py       # Interfaces with Gemini API
├── database/
│   └── db.py                  # Database helpers for SQLite & PostgreSQL
├── templates/
│   ├── chatbot_mits.html      # Main chat interface webpage
│   ├── chatbot_mits.css       # Premium custom styling sheet
│   └── chatbot_mits.js        # Websocket/API communication and chat logic
├── newmits_dataset/           # Contains raw/processed text files for the knowledge base
├── Dockerfile                 # Multi-stage Docker build recipe
├── docker-compose.yml         # Compose configuration file for local run
├── pyproject.toml             # Python dependency configuration
├── requirements.txt           # Standard Python requirements
└── vercel.json                # Vercel deployment configuration
```

---

## 📜 License
This project is licensed under the [MIT License](LICENSE).

---

## 📞 Contact
* **Developer:** PRODDUTURU LIKITH KUMAR 
* **Email:** Kumarlikith178@gmail.com
