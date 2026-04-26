import React from 'react';
import './ChatWindow.css';

function AnswerCard({ title, answer, metadata }) {
  if (!answer) return null;

  const normalizedAnswer = String(answer).replace(/\s+/g, ' ').trim();
  const backendCandidate = Array.isArray(metadata?.candidate_table)
    ? metadata.candidate_table.find((row) => row?.candidate_name && !/^Candidate\s+\d+$/i.test(row.candidate_name))
    : null;

  const candidateMatch = normalizedAnswer.match(
    /([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s+(?:is|appears|seems|looks)\b/
  );
  const candidateName = backendCandidate?.candidate_name || candidateMatch?.[1] || 'Not specified';

  const summaryRows = [
    { label: 'Candidate', value: candidateName },
    { label: 'Recommendation', value: normalizedAnswer },
  ];

  return (
    <div className="answer-card">
      <div className="answer-card-header">
        <h3>{title}</h3>
      </div>
      <div className="answer-summary-table-wrapper">
        <table className="answer-summary-table">
          <tbody>
            {summaryRows.map((row) => (
              <tr key={row.label}>
                <th scope="row">{row.label}</th>
                <td>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ChatWindow({ advancedAnswer, advancedMeta, advancedMetrics }) {
  if (!advancedAnswer) {
    return null;
  }

  return (
    <div className="chat-window">
      <h2>Answer</h2>
      <AnswerCard
        title="Advanced RAG"
        answer={advancedAnswer}
        metadata={advancedMeta}
      />
    </div>
  );
}

export default ChatWindow;
