# Setup Guide - Advanced Context-Aware RAG

## Prerequisites

- **Python 3.9+** (for backend)
- **Node.js 16+** (for frontend)
- **pip** (Python package manager)
- **npm** (Node package manager)
- **Git** (optional)

## Step-by-Step Setup

### Backend Setup

#### Step 1: Navigate to Backend Directory
```bash
cd backend
```

#### Step 2: Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

This installs:
- **FastAPI/Uvicorn**: Web framework
- **sentence-transformers**: Embeddings
- **faiss-cpu**: Vector search
- **networkx**: Graph operations
- **rank-bm25**: Keyword search
- **And more...**

#### Step 4: Verify Installation
```bash
python -c "from modules.embeddings import EmbeddingStore; print('✓ Backend ready')"
```

#### Step 5: Start Backend Server
```bash
python app.py
```

Or with more control:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

**Expected Output:**
```
INFO:     Started server process [1234]
INFO:     Waiting for application startup.
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Test API: Open `http://localhost:8000/docs` in browser

---

### Frontend Setup

#### Step 1: Navigate to Frontend Directory
```bash
cd ../frontend
```

#### Step 2: Install Dependencies
```bash
npm install
```

This installs:
- **React 18**: UI framework
- **Axios**: HTTP client
- **Recharts**: Data visualization
- **And more...**

#### Step 3: Configure API URL
Create `.env` file:
```bash
echo "REACT_APP_API_URL=http://localhost:8000/api" > .env
```

#### Step 4: Start Development Server
```bash
npm start
```

**Expected Output:**
```
Compiled successfully!

You can now view rag-advanced-ui in the browser.

  Local:            http://localhost:3000
  On Your Network:  http://xxx.xxx.xxx.xxx:3000
```

---

## Usage Guide

### 1. Upload Documents

1. Open **http://localhost:3000** in browser
2. Drag and drop PDF/TXT/MD files or click to browse
3. Click "Upload & Process"
4. Wait for documents to be indexed

**Supported Formats:**
- `.pdf` - PDF documents
- `.txt` - Plain text
- `.md` / `.markdown` - Markdown files

### 2. Select RAG Mode

Choose from:
- **Standard RAG**: Traditional cosine similarity
- **Compare Both**: Side-by-side comparison (recommended)
- **Advanced RAG**: Graph-enhanced with optimization

### 3. Ask a Question

1. Type query in search box
2. Press Enter or click "Search"
3. View results from selected mode(s)

**Example Queries:**
- "What are the main topics?"
- "Summarize this document"
- "What is the conclusion?"
- "Compare X and Y"

### 4. Analyze Results

**Each result shows:**
- **Rank**: Position in retrieval
- **Document name**: Source file
- **Scores**: Cosine/Hybrid/Reranking scores
- **Content**: Relevant excerpt
- **Metadata**: Compression status, etc.

### 5. Review Metrics

Scroll to bottom to see:
- **Latency comparison**: Processing time
- **Token usage**: Original vs compressed
- **Graph metrics**: Nodes explored
- **Aggregated stats**: Across all queries

---

## Configuration

### Backend Configuration

Create `backend/.env`:
```
API_HOST=0.0.0.0
API_PORT=8000
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LOG_LEVEL=INFO
```

### Frontend Configuration

Create `frontend/.env`:
```
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_DEBUG=false
```

---

## Troubleshooting

### Backend Issues

**Error: `ModuleNotFoundError: No module named 'sentence_transformers'`**
```bash
pip install sentence-transformers --upgrade
```

**Error: `FAISS not available`**
```bash
pip install faiss-cpu
# or for GPU:
# pip install faiss-gpu
```

**Error: `Port 8000 already in use`**
```bash
# Use different port:
uvicorn app:app --port 8001

# Or kill process on port 8000:
# Windows: netstat -ano | findstr :8000
# macOS/Linux: lsof -i :8000
```

**Embedding Model Download**
- First run downloads ~200MB model
- Stored in `~/.cache/huggingface/`
- Subsequent runs are fast

### Frontend Issues

**Error: `npm: command not found`**
- Install Node.js from https://nodejs.org/
- Restart terminal after installation

**Error: `EACCES: permission denied`** (macOS/Linux)
```bash
sudo npm install -g npm
```

**API connection failed**
- Verify backend is running: `http://localhost:8000/docs`
- Check `REACT_APP_API_URL` in `.env`
- Restart frontend: `npm start`

**Port 3000 already in use**
```bash
# Use different port:
PORT=3001 npm start
```

---

## Performance Tips

### For Large Documents

1. **Increase chunk size** in `app.py`:
   ```python
   processor = DocumentProcessor(chunk_size=1024, overlap=128)
   ```

2. **Use FAISS GPU**:
   ```bash
   pip install faiss-gpu
   ```

3. **Adjust embedding batch size**:
   ```python
   embeddings = embed_model.embed_batch(texts, batch_size=64)
   ```

### For Fast Retrieval

1. **Reduce top-k**:
   - Retrieve fewer documents initially
   - Let reranking refine results

2. **Disable graph traversal**:
   - Simpler queries may not need it

3. **Lower semantic threshold**:
   - More permissive graph edges
   - Faster exploration

---

## Advanced Customization

### Custom Embedding Model

Edit `backend/app.py`:
```python
embedding_store = EmbeddingStore(
    model_name="sentence-transformers/all-mpnet-base-v2"
)
```

Available models: https://www.sbert.net/docs/pretrained_models.html

### Adjust Hybrid Search Weight

Edit `backend/app.py`:
```python
hybrid_searcher = HybridSearcher(embedding_store, alpha=0.8)
# alpha=1.0: Dense only
# alpha=0.7: Default (70% dense, 30% BM25)
# alpha=0.5: Equal weight
# alpha=0.0: BM25 only
```

### Custom Reranking Strategy

Edit `backend/modules/reranker.py`:
```python
class CustomReranker:
    def rerank(self, query, documents):
        # Your custom logic here
        pass
```

### Context Compression Levels

Edit `backend/modules/context_optimizer.py`:
```python
# Conservative (less compression)
optimized_docs, stats = optimizer.optimize_context(
    docs, compression=True, dedup=False, min_relevance=0.1
)

# Aggressive (more compression)
optimized_docs, stats = optimizer.optimize_context(
    docs, compression=True, dedup=True, min_relevance=0.7
)
```

---

## Docker Deployment (Optional)

### Build Docker Image

Create `Dockerfile` in root:
```dockerfile
FROM python:3.9

WORKDIR /app

# Backend
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

# Frontend build
FROM node:16 AS frontend-build
WORKDIR /app/frontend
COPY frontend .
RUN npm install && npm run build

# Final
FROM python:3.9
WORKDIR /app
COPY --from=build /app/backend .
COPY --from=frontend-build /app/frontend/build ./public

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Run with Docker

```bash
# Build
docker build -t rag-advanced .

# Run
docker run -p 8000:8000 -p 3000:3000 rag-advanced
```

---

## Production Deployment

### Using Gunicorn (Backend)

```bash
pip install gunicorn
gunicorn app:app -w 4 -b 0.0.0.0:8000
```

### Using PM2 (Node/Frontend)

```bash
npm install -g pm2
pm2 start "npm start" --name rag-frontend
pm2 startup
pm2 save
```

### Using Nginx (Reverse Proxy)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
    }
}
```

---

## Testing

### Backend Tests

```bash
# Manual API test
curl http://localhost:8000/api/health

# Upload test
curl -X POST -F "files=@test.pdf" http://localhost:8000/api/upload

# Query test
curl "http://localhost:8000/api/retrieve/standard?query=test&k=5"
```

### Frontend Tests

```bash
npm test  # Run Jest tests

# Manual testing
# 1. Upload a document
# 2. Submit several queries
# 3. Compare mode results
# 4. Check metrics panel
```

---

## Next Steps

1. **Customize Embedding Model**: Try different pre-trained models
2. **Tune Hybrid Alpha**: Test different dense/sparse ratios
3. **Optimize Chunk Size**: Based on your document type
4. **Add LLM Integration**: Connect to OpenAI/Anthropic/Local LLM
5. **Deploy to Production**: Use Docker + Cloud provider

---

## Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Docs**: https://react.dev/
- **Sentence-transformers**: https://www.sbert.net/
- **FAISS**: https://github.com/facebookresearch/faiss
- **NetworkX**: https://networkx.org/

---

## Getting Help

1. Check troubleshooting section
2. Review API docs: `http://localhost:8000/docs`
3. Check browser console for frontend errors
4. Check terminal output for backend errors
5. Review component prop types in source code

---

**You're all set! Happy RAG-ing! 🚀**
