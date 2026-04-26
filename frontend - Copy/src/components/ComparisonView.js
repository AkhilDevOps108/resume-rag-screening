import React from 'react';
import './ComparisonView.css';

function ComparisonView({ comparison }) {
  const standard = comparison.standard_rag;
  const advanced = comparison.advanced_rag;
  const comp = comparison.comparison_metrics;

  const getImprovementColor = (value) => {
    if (value > 0) return '#10b981';
    if (value < 0) return '#ef4444';
    return '#999';
  };

  return (
    <div className="comparison-container">
      <h2>📊 Side-by-Side Comparison</h2>
      <div className="comparison-grid">
        {/* Latency Comparison */}
        <div className="comparison-card">
          <div className="card-title">⚡ Latency</div>
          <div className="comparison-row">
            <div className="mode-column">
              <span className="mode-name">Standard RAG</span>
              <span className="metric-value">{standard.metrics.latency_ms.toFixed(2)} ms</span>
            </div>
            <div className="vs-divider">vs</div>
            <div className="mode-column">
              <span className="mode-name">Advanced RAG</span>
              <span className="metric-value">{advanced.metrics.latency_ms.toFixed(2)} ms</span>
            </div>
          </div>
          {comp.latency_difference_ms !== undefined && (
            <div className="improvement">
              <span
                style={{ color: comp.latency_difference_ms > 0 ? '#ef4444' : '#10b981' }}
              >
                {comp.latency_difference_ms > 0 ? '+' : ''}
                {comp.latency_difference_ms.toFixed(2)} ms
              </span>
            </div>
          )}
        </div>

        {/* Score Comparison */}
        <div className="comparison-card">
          <div className="card-title">📈 Retrieval Score</div>
          <div className="comparison-row">
            <div className="mode-column">
              <span className="mode-name">Standard RAG</span>
              <span className="metric-value">{standard.avg_score.toFixed(3)}</span>
            </div>
            <div className="vs-divider">vs</div>
            <div className="mode-column">
              <span className="mode-name">Advanced RAG</span>
              <span className="metric-value">{advanced.avg_score.toFixed(3)}</span>
            </div>
          </div>
          {comp.score_improvement !== undefined && (
            <div className="improvement">
              <span style={{ color: getImprovementColor(comp.score_improvement) }}>
                {comp.score_improvement > 0 ? '+' : ''}
                {comp.score_improvement.toFixed(3)}
              </span>
            </div>
          )}
        </div>

        {/* Document Count */}
        <div className="comparison-card">
          <div className="card-title">📄 Documents Retrieved</div>
          <div className="comparison-row">
            <div className="mode-column">
              <span className="mode-name">Standard RAG</span>
              <span className="metric-value">{standard.num_docs}</span>
            </div>
            <div className="vs-divider">vs</div>
            <div className="mode-column">
              <span className="mode-name">Advanced RAG</span>
              <span className="metric-value">{advanced.num_docs}</span>
            </div>
          </div>
        </div>

        {/* Token Usage */}
        <div className="comparison-card">
          <div className="card-title">🔤 Token Usage</div>
          <div className="comparison-row">
            <div className="mode-column">
              <span className="mode-name">Standard RAG</span>
              <span className="metric-value">{standard.metrics.total_tokens}</span>
            </div>
            <div className="vs-divider">vs</div>
            <div className="mode-column">
              <span className="mode-name">Advanced RAG</span>
              <span className="metric-value">{advanced.metrics.total_tokens}</span>
            </div>
          </div>
          {comp.token_reduction_pct > 0 && (
            <div className="improvement">
              <span style={{ color: '#10b981' }}>
                ↓ {comp.token_reduction_pct.toFixed(1)}% reduction
              </span>
            </div>
          )}
        </div>

        {/* Graph Nodes */}
        <div className="comparison-card">
          <div className="card-title">🌐 Graph Nodes Explored</div>
          <div className="comparison-row">
            <div className="mode-column">
              <span className="mode-name">Standard RAG</span>
              <span className="metric-value">—</span>
            </div>
            <div className="vs-divider">vs</div>
            <div className="mode-column">
              <span className="mode-name">Advanced RAG</span>
              <span className="metric-value">{comp.graph_nodes_explored}</span>
            </div>
          </div>
        </div>

        {/* Pipeline Stages */}
        <div className="comparison-card">
          <div className="card-title">🔄 Pipeline Complexity</div>
          <div className="comparison-row">
            <div className="mode-column">
              <span className="mode-name">Standard RAG</span>
              <span className="metric-value">{standard.metrics.pipeline_stages.length}</span>
            </div>
            <div className="vs-divider">vs</div>
            <div className="mode-column">
              <span className="mode-name">Advanced RAG</span>
              <span className="metric-value">{advanced.metrics.pipeline_stages.length}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Top Documents Comparison */}
      <div className="top-docs-comparison">
        <div className="comparison-section">
          <h3>Top Documents - Standard RAG</h3>
          <div className="docs-list">
            {standard.top_docs.map((doc, idx) => (
              <div key={idx} className="doc-item">
                <span className="doc-rank">#{idx + 1}</span>
                <span className="doc-info">
                  <strong>{doc.title}</strong>
                  <br />
                  <small>Score: {doc.score.toFixed(3)} | Length: {doc.content_length} words</small>
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="comparison-section">
          <h3>Top Documents - Advanced RAG</h3>
          <div className="docs-list">
            {advanced.top_docs.map((doc, idx) => (
              <div key={idx} className="doc-item">
                <span className="doc-rank">#{idx + 1}</span>
                <span className="doc-info">
                  <strong>{doc.title}</strong>
                  <br />
                  <small>
                    Score: {doc.score.toFixed(3)} | Length: {doc.content_length} words
                    {doc.compressed && ' | 🗜️ Compressed'}
                  </small>
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default ComparisonView;
