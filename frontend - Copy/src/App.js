import React, { useState, useEffect, useCallback } from 'react';
import './App.css';
import DocumentUpload from './components/DocumentUpload';
import QueryInterface from './components/QueryInterface';
import ChatWindow from './components/ChatWindow';

function App() {
  const [documentsLoaded, setDocumentsLoaded] = useState(false);
  const [documentStats, setDocumentStats] = useState(null);
  const [advancedResults, setAdvancedResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [queryError, setQueryError] = useState('');

  const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

  const getDocumentStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/documents`);
      const data = await response.json();
      setDocumentStats(data);
      setDocumentsLoaded((data?.total_chunks || 0) > 0);
    } catch (error) {
      console.error('Failed to fetch document stats:', error);
    }
  }, [API_BASE]);

  const checkStatus = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/health`);
      const data = await response.json();
      if (data.ready) {
        setDocumentsLoaded(true);
        await getDocumentStats();
      }
    } catch (error) {
      console.error('Health check failed:', error);
    }
  }, [API_BASE, getDocumentStats]);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const handleDocumentsUploaded = async () => {
    setDocumentsLoaded(true);
    await getDocumentStats();
  };

  const handleQuery = async (query) => {
    if (!documentsLoaded) {
      alert('Please upload at least one document before asking questions.');
      return;
    }

    setLoading(true);
    setQueryError('');
    setAdvancedResults(null);

    try {
      const parseApiResponse = async (response) => {
        let data = {};
        try {
          data = await response.json();
        } catch {
          data = {};
        }

        if (!response.ok) {
          throw new Error(data?.detail || `Request failed (${response.status})`);
        }

        return data;
      };

      const response = await fetch(
        `${API_BASE}/retrieve?query=${encodeURIComponent(query)}&k=5`
      );
      const data = await parseApiResponse(response);

      if (!data?.metrics || !Array.isArray(data?.retrieved_docs)) {
        throw new Error('Advanced RAG returned an invalid response format.');
      }

      setAdvancedResults(data);
    } catch (error) {
      console.error('Query failed:', error);
      setQueryError(error.message || 'Query failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <h1>🚀 Advanced Context-Aware RAG</h1>
          <p>Graph-enhanced retrieval, reranking, and context optimization</p>
        </div>
      </header>

      <div className="app-container">
        <div className="workspace-layout">
          <section className="upload-panel">
            <DocumentUpload onDocumentsUploaded={handleDocumentsUploaded} />

            <div className="upload-panel-footer">
              {documentStats ? (
                <p>
                  <strong>{documentStats.total_documents}</strong> files indexed across{' '}
                  <strong>{documentStats.total_chunks}</strong> chunks.
                </p>
              ) : (
                <p>Upload PDF, TXT, or Markdown files to build the retrieval context.</p>
              )}
            </div>
          </section>

          <main className="query-panel">
            <div className="query-panel-header">
              <h2>Ask Questions</h2>
              <p>Query the indexed documents with the Advanced Context-Aware RAG pipeline.</p>
            </div>

            {!documentsLoaded && (
              <div className="notice-card">
                Upload at least one document to enable question answering.
              </div>
            )}

            <QueryInterface onQuery={handleQuery} loading={loading} disabled={!documentsLoaded} />

            {queryError && <div className="error-card">{queryError}</div>}

            <ChatWindow
              advancedAnswer={advancedResults?.answer}
              advancedMeta={advancedResults?.answer_metadata}
              advancedMetrics={advancedResults?.metrics}
            />

            {loading && <div className="loading-spinner">Processing query...</div>}
          </main>
        </div>
      </div>

      <footer className="app-footer">
        <p>Advanced RAG System © 2024 | Powered by Semantic Graphs & Context Optimization</p>
      </footer>
    </div>
  );
}

export default App;
