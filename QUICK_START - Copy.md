# Quick Start - Advanced Context-Aware RAG

This guide gets the current application running locally with the advanced-only flow.

## What You Will Run

- FastAPI backend on port `8000`
- React frontend on port `3000`
- Advanced retrieval pipeline through `/api/retrieve`
- Gemini-backed answer generation if `GEMINI_API_KEY` is set

## 1. Start The Backend

From `backend/`:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Backend URLs:

- API base: `http://localhost:8000/api`
- Health: `http://localhost:8000/api/health`
- Docs: `http://localhost:8000/docs`

## 2. Configure Backend Environment

Create `backend/.env` with at least:

```env
API_HOST=0.0.0.0
API_PORT=8000
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_FORCE_LOCAL=false
GEMINI_API_KEY=AEvYahfgBYzd8
GEMINI_MODEL=gemini-2.5-flash
```

Notes:

- Set `EMBEDDING_FORCE_LOCAL=true` only if your environment cannot download or use the transformer model
- Gemini is the preferred answer path; without it, the backend may fall back to local answer synthesis

## 3. Start The Frontend

From `frontend/` in a new terminal:

```bash
npm install
npm start
```

Optional `frontend/.env`:

```env
REACT_APP_API_URL=http://localhost:8000/api
```

Frontend URL:

- App: `http://localhost:3000`

## 4. Use The App

### Upload documents

- Click the upload area to open the file picker, or drag files into it
- Supported types: PDF, TXT, MD, MARKDOWN
- Wait for indexing to complete

### Ask questions

- Enter your question in the right panel
- The frontend sends the query to `GET /api/retrieve`
- The backend returns the final answer and metadata

## Current UI Layout

- Left side: upload panel
- Right side: question box and answer window
- Dark mode throughout the main workspace

## Current Retrieval Pipeline

```text
Query
-> Hybrid retrieval
-> Reranking
-> Semantic graph traversal
-> Context optimization
-> Gemini answer generation
```

## Main Endpoints

- `POST /api/upload` - upload and index documents
- `GET /api/documents` - document stats
- `GET /api/health` - readiness check
- `GET /api/retrieve?query=...&k=5` - ask a question

## Quick Verification

After both servers are running:

1. Open `http://localhost:3000`
2. Upload one small PDF or TXT file
3. Ask a direct factual question from that file
4. Confirm an answer appears in the chat window

## If Answers Look Weak

Check these first:

- Gemini API key is present and valid
- Backend was restarted after `.env` changes
- The uploaded file actually contains extractable text
- `EMBEDDING_FORCE_LOCAL` is not enabled unless necessary

## Common Issues

### File picker does not open

- Restart the frontend dev server so the latest upload component is loaded

### Upload works but answers are poor

- Verify the file text is readable
- Verify Gemini is configured
- Prefer transformer embeddings over local hashing fallback

### Query request fails

- Confirm backend is running on port `8000`
- Check `REACT_APP_API_URL`
- Open `http://localhost:8000/api/health`

## Related Docs

- `README.md` for the feature overview
- `ARCHITECTURE.md` for the system design
- `SETUP.md` for deeper installation and troubleshooting guidance
| Frontend won't connect to API | Check `.env` has correct API_URL |
| Embeddings model download fails | Check internet connection, disk space |
| Slow document upload | Increase chunk size, reduce overlap |
| Out of memory | Reduce batch size, process fewer documents |

See `SETUP.md` for detailed troubleshooting.

---

## 📞 Support Resources

- **API Docs**: `http://localhost:8000/docs` (Swagger UI)
- **React DevTools**: Browser extension for debugging
- **Python Logging**: Check terminal output for detailed logs
- **Network Tab**: Browser DevTools for API calls

---

## 🎉 You're All Set!

Everything is ready to go. The system is:
- ✅ Production-quality code
- ✅ Fully documented
- ✅ Easily customizable
- ✅ Containerized for deployment
- ✅ Optimized for performance

**Start exploring the difference between Standard RAG and Advanced Context-Aware RAG!**

---

**Built with ❤️ for advanced RAG research and production use**

Next command: `cd backend && python app.py` 🚀
