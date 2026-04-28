import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage2.css';

function identityForLabel(label, labelToModel, labelMetadata) {
  const meta = labelMetadata?.[label] || {};
  return {
    displayName: meta.display_name || labelToModel?.[label] || label,
    requestedAlias: meta.requested_alias,
    requestedTech: meta.requested_technical_name,
    actualAlias: meta.actual_alias || meta.requested_alias,
    actualTech: meta.technical_name,
    fallbackUsed: meta.fallback_used,
    fallbackReason: meta.fallback_reason,
  };
}

function identityForItem(item) {
  const meta = item.metadata || {};
  return {
    displayName: item.display_name || meta.display_name || item.model,
    requestedAlias: meta.requested_alias || item.alias,
    requestedTech: meta.requested_technical_name,
    actualAlias: meta.actual_alias || meta.requested_alias || item.alias,
    actualTech: item.technical_name || meta.technical_name,
    fallbackUsed: meta.fallback_used,
    fallbackReason: meta.fallback_reason,
  };
}

function deAnonymizeText(text, labelToModel, labelMetadata) {
  if (!labelToModel) return text;

  let result = text;
  // Replace each "Response X" with clean display identity for readability.
  Object.entries(labelToModel).forEach(([label, model]) => {
    const identity = identityForLabel(label, labelToModel, labelMetadata);
    const name = identity.displayName || model;
    result = result.replace(new RegExp(label, 'g'), `**${label} (${name})**`);
  });
  return result;
}

export default function Stage2({ rankings, labelToModel, labelMetadata, aggregateRankings }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!rankings || rankings.length === 0) {
    return null;
  }

  return (
    <div className="stage stage2">
      <h3 className="stage-title">Stage 2: Peer Rankings</h3>

      <h4>Raw Evaluations</h4>
      <p className="stage-description">
        Each model evaluated all responses (anonymized as Response A, B, C, etc.) and provided rankings.
        Below, model names are shown in <strong>bold</strong> for readability, but the original evaluation used anonymous labels.
      </p>

      <div className="tabs">
        {rankings.map((rank, index) => (
          (() => {
            const identity = identityForItem(rank);
            return (
          <button
            key={index}
            className={`tab ${activeTab === index ? 'active' : ''}`}
            onClick={() => setActiveTab(index)}
          >
            {identity.displayName}
          </button>
            );
          })()
        ))}
      </div>

      <div className="tab-content">
        {(() => {
          const identity = identityForItem(rankings[activeTab]);
          return (
            <div className="ranking-model">
              <div className="identity-display">{identity.displayName}</div>
              <div>requested: {identity.requestedAlias} -&gt; {identity.requestedTech}</div>
              <div>actual: {identity.actualAlias} -&gt; {identity.actualTech}</div>
              <div>fallback: {identity.fallbackUsed ? 'yes' : 'no'}</div>
              {identity.fallbackReason && <div>reason: {identity.fallbackReason}</div>}
            </div>
          );
        })()}
        <div className="ranking-content markdown-content">
          <ReactMarkdown>
            {deAnonymizeText(rankings[activeTab].ranking, labelToModel, labelMetadata)}
          </ReactMarkdown>
        </div>

        {rankings[activeTab].parsed_ranking &&
         rankings[activeTab].parsed_ranking.length > 0 && (
          <div className="parsed-ranking">
            <strong>Extracted Ranking:</strong>
            <ol>
              {rankings[activeTab].parsed_ranking.map((label, i) => (
                <li key={i}>
                  {label} - {identityForLabel(label, labelToModel, labelMetadata).displayName}
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>

      {aggregateRankings && aggregateRankings.length > 0 && (
        <div className="aggregate-rankings">
          <h4>Aggregate Rankings (Street Cred)</h4>
          <p className="stage-description">
            Combined results across all peer evaluations (lower score is better):
          </p>
          <div className="aggregate-list">
            {aggregateRankings.map((agg, index) => (
              <div key={index} className="aggregate-item">
                <span className="rank-position">#{index + 1}</span>
                <span className="rank-model">
                  <span className="rank-label">{agg.display_name || agg.model}</span>
                  <span className="rank-detail">Alias: {agg.requested_alias || 'unknown'}</span>
                  <span className="rank-detail">Actual: {agg.technical_name || 'unknown'}</span>
                  <span className="rank-detail">Fallback: {agg.fallback_used ? 'yes' : 'no'}</span>
                </span>
                <span className="rank-score">
                  Avg: {agg.average_rank.toFixed(2)}
                </span>
                <span className="rank-count">
                  ({agg.rankings_count} votes)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
