import React, { useState } from 'react';
import './QueryInterface.css';

function QueryInterface({ onQuery, loading, disabled = false }) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim()) {
      onQuery(query);
      setQuery('');
    }
  };

  return (
    <div className="query-interface">
      <form onSubmit={handleSubmit} className="query-form">
        <div className="input-wrapper">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={disabled ? 'Upload documents to start asking questions...' : 'Ask a question about your documents...'}
            disabled={loading || disabled}
            className="query-input"
          />
          <button
            type="submit"
            disabled={loading || disabled || !query.trim()}
            className="query-btn"
          >
            {loading ? '⏳ Processing...' : '🔍 Search'}
          </button>
        </div>
      </form>

      <div className="query-hints">
        <span className="hint-label">Try asking:</span>
        <button
          className="hint-btn"
          onClick={() => onQuery('What are the main topics?')}
          disabled={loading || disabled}
        >
          Topics
        </button>
        <button
          className="hint-btn"
          onClick={() => onQuery('Summarize the key points')}
          disabled={loading || disabled}
        >
          Summary
        </button>
        <button
          className="hint-btn"
          onClick={() => onQuery('What is the conclusion?')}
          disabled={loading || disabled}
        >
          Conclusion
        </button>
      </div>
    </div>
  );
}

export default QueryInterface;
