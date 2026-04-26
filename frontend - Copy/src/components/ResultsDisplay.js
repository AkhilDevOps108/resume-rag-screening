import React, { useState } from 'react';
import './ResultsDisplay.css';

function ResultsDisplay({ results, title, mode }) {
  const [expandedDoc, setExpandedDoc] = useState(null);
  const metrics = results?.metrics || {};
  const retrievedDocs = Array.isArray(results?.retrieved_docs) ? results.retrieved_docs : [];
  const pipelineStages = Array.isArray(metrics?.pipeline_stages) ? metrics.pipeline_stages : [];

  const getScoreColor = (score) => {
    if (score >= 0.8) return '#10b981';
    if (score >= 0.6) return '#f59e0b';
    return '#ef4444';
  };

  if (!metrics || !Array.isArray(results?.retrieved_docs)) {
    return (
      <div className="results-container">
        <div className="no-results">
          <p>{results?.detail || 'Result data is unavailable for this request.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="results-container">
      <div className="results-header">
        <h2>{title}</h2>
        <div className="results-meta">
          <span className="meta-item">
            📄 <strong>{results.num_retrieved || retrievedDocs.length}</strong> Documents Retrieved
          </span>
          <span className="meta-item">
            ⚡ <strong>{Number(metrics.latency_ms || 0).toFixed(2)}</strong> ms
          </span>
          <span className="meta-item">
            🔤 <strong>{metrics.total_tokens || 0}</strong> Tokens
          </span>
        </div>
      </div>

      {mode === 'advanced' && metrics.graph_metrics && (
        <div className="advanced-metrics">
          <div className="metric-box">
            <span className="metric-label">Graph Nodes Explored</span>
            <span className="metric-value">{metrics.graph_metrics.num_nodes}</span>
          </div>
          {metrics.token_reduction_pct > 0 && (
            <div className="metric-box">
              <span className="metric-label">Token Reduction</span>
              <span className="metric-value">{metrics.token_reduction_pct.toFixed(1)}%</span>
            </div>
          )}
          <div className="metric-box">
            <span className="metric-label">Pipeline Stages</span>
            <span className="metric-value">{pipelineStages.length}</span>
          </div>
        </div>
      )}

      <div className="pipeline-visualization">
        <div className="pipeline-label">Pipeline:</div>
        <div className="pipeline-stages">
          {pipelineStages.map((stage, idx) => (
            <div key={idx} className="pipeline-stage">
              <span>{stage.replace(/_/g, ' ')}</span>
              {idx < pipelineStages.length - 1 && <span className="arrow">→</span>}
            </div>
          ))}
        </div>
      </div>

      <div className="documents-grid">
        {retrievedDocs.map((doc) => (
          <div key={doc.chunk_id} className="document-card">
            <div className="doc-header">
              <div className="doc-rank">#{doc.rank}</div>
              <div className="doc-title">{doc.doc_name}</div>
              <div className="doc-scores">
                {doc.cosine_score !== undefined && (
                  <div
                    className="score-badge"
                    style={{
                      background: getScoreColor(doc.cosine_score),
                      color: 'white'
                    }}
                  >
                    Cosine: {doc.cosine_score.toFixed(3)}
                  </div>
                )}
                {doc.reranking_score !== undefined && (
                  <div
                    className="score-badge"
                    style={{
                      background: getScoreColor(doc.reranking_score)
                    }}
                  >
                    Rerank: {doc.reranking_score.toFixed(3)}
                  </div>
                )}
                {doc.hybrid_score !== undefined && (
                  <div
                    className="score-badge"
                    style={{
                      background: getScoreColor(doc.hybrid_score)
                    }}
                  >
                    Hybrid: {doc.hybrid_score.toFixed(3)}
                  </div>
                )}
              </div>
            </div>

            <div className="doc-content">
              <p className={expandedDoc === doc.chunk_id ? 'expanded' : ''}>
                {doc.content}
              </p>
            </div>

            {doc.compressed && (
              <div className="doc-info">
                <span className="info-badge">🗜️ Compressed</span>
              </div>
            )}

            <button
              className="expand-btn"
              onClick={() => setExpandedDoc(expandedDoc === doc.chunk_id ? null : doc.chunk_id)}
            >
              {expandedDoc === doc.chunk_id ? '▼ Show Less' : '▶ Show More'}
            </button>
          </div>
        ))}
      </div>

      {retrievedDocs.length === 0 && (
        <div className="no-results">
          <p>No documents retrieved. Try refining your query.</p>
        </div>
      )}
    </div>
  );
}

export default ResultsDisplay;
