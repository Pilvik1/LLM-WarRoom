import ReactMarkdown from 'react-markdown';
import './Stage3.css';

function identityForFinal(finalResponse) {
  const meta = finalResponse.metadata || {};
  return {
    displayName: finalResponse.display_name || meta.display_name || finalResponse.model,
    requestedAlias: finalResponse.requested_alias || meta.requested_alias,
    requestedTech: meta.requested_technical_name,
    actualAlias: meta.actual_alias || meta.requested_alias,
    actualTech: finalResponse.technical_name || meta.technical_name,
    fallbackUsed: finalResponse.fallback_used ?? meta.fallback_used,
    fallbackReason: finalResponse.fallback_reason || meta.fallback_reason,
  };
}

export default function Stage3({ finalResponse }) {
  if (!finalResponse) {
    return null;
  }
  const identity = identityForFinal(finalResponse);

  return (
    <div className="stage stage3">
      <h3 className="stage-title">Stage 3: Final Synthesis</h3>
      <div className="final-response">
        <div className="chairman-label">
          <div className="identity-display">Synthesizer: {identity.displayName}</div>
          <div>requested: {identity.requestedAlias} -&gt; {identity.requestedTech}</div>
          <div>actual: {identity.actualAlias} -&gt; {identity.actualTech}</div>
          <div>fallback: {identity.fallbackUsed ? 'yes' : 'no'}</div>
          {identity.fallbackReason && <div>reason: {identity.fallbackReason}</div>}
        </div>
        <div className="final-text markdown-content">
          <ReactMarkdown>{finalResponse.response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
