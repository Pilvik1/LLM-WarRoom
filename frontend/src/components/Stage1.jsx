import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './Stage1.css';

function identityLines(item) {
  const meta = item.metadata || {};
  const displayName = item.display_name || meta.display_name || item.model;
  const requestedAlias = item.requested_alias || meta.requested_alias || item.alias;
  const requestedTech = meta.requested_technical_name || item.technical_name || meta.technical_name;
  const actualAlias = meta.actual_alias || requestedAlias;
  const actualTech = item.technical_name || meta.technical_name || requestedTech;
  const fallbackUsed = item.fallback_used ?? meta.fallback_used;
  const fallbackReason = item.fallback_reason || meta.fallback_reason;

  return {
    displayName,
    requestedAlias,
    requestedTech,
    actualAlias,
    actualTech,
    fallbackUsed,
    fallbackReason,
  };
}

export default function Stage1({ responses }) {
  const [activeTab, setActiveTab] = useState(0);

  if (!responses || responses.length === 0) {
    return null;
  }

  return (
    <div className="stage stage1">
      <h3 className="stage-title">Stage 1: Individual Responses</h3>

      <div className="tabs">
        {responses.map((resp, index) => (
          (() => {
            const identity = identityLines(resp);
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
          const identity = identityLines(responses[activeTab]);
          return (
            <div className="model-name">
              <div className="identity-display">{identity.displayName}</div>
              <div>requested: {identity.requestedAlias} -&gt; {identity.requestedTech}</div>
              <div>actual: {identity.actualAlias} -&gt; {identity.actualTech}</div>
              <div>fallback: {identity.fallbackUsed ? 'yes' : 'no'}</div>
              {identity.fallbackReason && (
                <div>reason: {identity.fallbackReason}</div>
              )}
            </div>
          );
        })()}
        <div className="response-text markdown-content">
          <ReactMarkdown>{responses[activeTab].response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
