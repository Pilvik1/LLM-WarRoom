import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from '../api';
import './CaseWorkbench.css';

const MODES = [
  { id: 'ask', label: 'Ask' },
  { id: 'war_room', label: 'War Room' },
];

const DEFAULT_CANDIDATES = [
  { id: 'cand_a', title: '', content: '' },
  { id: 'cand_b', title: '', content: '' },
];

function splitCriteria(value) {
  return value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseJsonField(value, label) {
  if (!value.trim()) {
    return {};
  }
  try {
    return JSON.parse(value);
  } catch (error) {
    throw new Error(`${label} must be valid JSON: ${error.message}`);
  }
}

function artifactPath(result) {
  return (
    result?.artifact?.path ||
    result?.artifact_paths?.run_json ||
    result?.artifact_paths?.decision_json ||
    ''
  );
}

function resultItems(result) {
  if (!result) return [];
  return (
    result.advisor_responses ||
    result.evaluations ||
    result.critiques ||
    result.comparisons ||
    []
  );
}

function itemText(item) {
  return item.evaluation || item.critique || item.comparison || item.response || '';
}

function itemTitle(item, index) {
  const role = item.advisor_name || `Item ${index + 1}`;
  return `${role} · ${modelDisplayLabel(item)}`;
}

function synthesisText(result) {
  return result?.synthesis?.response || result?.synthesis?.raw_output || '';
}

function decisionText(result) {
  if (!result?.decision) return '';
  return `Decision: ${result.decision}\n\nReason: ${result.reason || 'No reason recorded.'}`;
}

function verdictText(result) {
  return result?.verdict?.response || result?.verdict?.raw_output || '';
}

function metadataFor(item) {
  return item?.metadata || {};
}

function modelDisplayLabel(item) {
  const meta = metadataFor(item);
  const requested = item?.display_name || meta.display_name || item?.model || item?.alias || 'Unknown model';
  const actual = item?.actual_display_name || meta.actual_display_name || actualLabelFromMeta(item);
  const fallbackUsed = item?.fallback_used ?? meta.fallback_used;
  if (fallbackUsed && actual && actual !== requested) {
    return `${requested} -> ${actual} fallback`;
  }
  if (fallbackUsed) {
    return `${requested} fallback`;
  }
  return requested;
}

function actualLabelFromMeta(item) {
  const meta = metadataFor(item);
  const actualProvider = item?.actual_provider || meta.actual_provider;
  const actualModel = item?.actual_model || meta.actual_model;
  if (actualProvider && actualModel) {
    return `${actualProvider}/${actualModel}`;
  }
  return '';
}

function technicalLine(provider, model) {
  if (!provider && !model) return 'unknown';
  if (!provider) return model;
  if (!model) return provider;
  return `${provider}/${model}`;
}

function modelDetails(item) {
  const meta = metadataFor(item);
  return {
    requestedAlias: item?.requested_alias || meta.requested_alias || item?.alias,
    requested: technicalLine(
      item?.requested_provider || meta.requested_provider,
      item?.requested_model || meta.requested_model
    ),
    actual: technicalLine(
      item?.actual_provider || meta.actual_provider,
      item?.actual_model || meta.actual_model
    ),
    fallbackUsed: item?.fallback_used ?? meta.fallback_used,
    fallbackReason: item?.fallback_reason || meta.fallback_reason,
  };
}

function oneThingToDoFirst(verdict) {
  if (!verdict) return '';
  const match = verdict.match(/## The One Thing to Do First\s+([\s\S]*?)(?=\n## |\s*$)/i);
  return match?.[1]?.trim() || '';
}

export default function CaseWorkbench({ mode, onModeChange }) {
  const [task, setTask] = useState('');
  const [candidateOutput, setCandidateOutput] = useState('');
  const [context, setContext] = useState('');
  const [stakes, setStakes] = useState('');
  const [criteria, setCriteria] = useState('');
  const [candidates, setCandidates] = useState(DEFAULT_CANDIDATES);
  const [sourceRunId, setSourceRunId] = useState('');
  const [thresholdsJson, setThresholdsJson] = useState('{\n  "min_revision_ratio": 0.5\n}');
  const [rulesJson, setRulesJson] = useState('{}');
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const updateCandidate = (index, field, value) => {
    setCandidates((prev) =>
      prev.map((candidate, candidateIndex) =>
        candidateIndex === index ? { ...candidate, [field]: value } : candidate
      )
    );
  };

  const addCandidate = () => {
    setCandidates((prev) => [
      ...prev,
      { id: `cand_${String.fromCharCode(97 + prev.length)}`, title: '', content: '' },
    ]);
  };

  const removeCandidate = (index) => {
    setCandidates((prev) => prev.filter((_, candidateIndex) => candidateIndex !== index));
  };

  const runCase = async (event) => {
    event.preventDefault();
    setError('');
    setResult(null);
    setIsSubmitting(true);

    try {
      let response;
      if (mode === 'evaluate') {
        if (!candidateOutput.trim()) {
          throw new Error('candidate_output is required.');
        }
        response = await api.evaluateCase({
          task,
          candidate_output: candidateOutput,
          criteria: splitCriteria(criteria),
        });
      } else if (mode === 'critique') {
        if (!candidateOutput.trim()) {
          throw new Error('candidate_output/artifact is required.');
        }
        response = await api.critiqueCase({
          task,
          artifact: candidateOutput,
          criteria: splitCriteria(criteria),
        });
      } else if (mode === 'compare') {
        const cleanCandidates = candidates.map((candidate) => ({
          id: candidate.id.trim(),
          title: candidate.title.trim(),
          content: candidate.content.trim(),
        }));
        if (cleanCandidates.length < 2) {
          throw new Error('Compare requires at least two candidates.');
        }
        response = await api.compareCase({
          task,
          candidates: cleanCandidates,
          criteria: splitCriteria(criteria),
        });
      } else if (mode === 'decide') {
        if (!sourceRunId.trim()) {
          throw new Error('source_run_id is required for this workbench form.');
        }
        response = await api.decideCase({
          source_run_id: sourceRunId.trim(),
          thresholds: parseJsonField(thresholdsJson, 'Thresholds'),
          rules: parseJsonField(rulesJson, 'Rules'),
        });
      } else if (mode === 'war_room') {
        response = await api.warRoomCase({
          task,
          context,
          stakes,
          candidate_output: candidateOutput,
          criteria: splitCriteria(criteria),
        });
      }
      setResult(response);
    } catch (err) {
      setError(err.message || 'The backend request failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="case-workbench">
      <div className="workbench-header">
        <div>
          <h2>War Room</h2>
          <p>Pressure-test a decision, idea, plan, or tradeoff using multiple advisor lenses.</p>
        </div>
        <div className="mode-selector" role="tablist" aria-label="Case mode">
          {MODES.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`mode-button ${mode === item.id ? 'active' : ''}`}
              onClick={() => onModeChange(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>

      <form className="workbench-form" onSubmit={runCase}>
        {mode !== 'decide' && (
          <label className="field primary-field">
            <span>What should the War Room pressure-test?</span>
            <small>Rough input is fine. The War Room will frame the question and state assumptions.</small>
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              rows={5}
              placeholder="Should I build a simple habit-tracking app with AI weekly reflections, or is it too generic?"
            />
          </label>
        )}

        {mode === 'war_room' && (
          <div className="optional-sections">
            <OptionalSection
              title="Add more context"
              explainer="Useful if the War Room needs background about you, the project, audience, constraints, or prior decisions."
            >
              <label className="field">
                <span>Context</span>
                <textarea
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  rows={4}
                  placeholder="Example: I’m building this as a local-first personal tool. I care more about learning and utility than monetization right now."
                />
              </label>
            </OptionalSection>

            <OptionalSection
              title="Add stakes"
              explainer="Useful if the decision has real cost, opportunity cost, risk, or consequences."
            >
              <label className="field">
                <span>Stakes</span>
                <textarea
                  value={stakes}
                  onChange={(e) => setStakes(e.target.value)}
                  rows={3}
                  placeholder="Example: This affects whether I spend the next two weeks building the MVP or move on."
                />
              </label>
            </OptionalSection>

            <OptionalSection
              title="Add criteria"
              explainer="Useful if you want the War Room to judge the idea by specific standards."
            >
              <label className="field">
                <span>Criteria</span>
                <textarea
                  value={criteria}
                  onChange={(e) => setCriteria(e.target.value)}
                  rows={5}
                  placeholder={`Example:
- usefulness
- differentiation
- ease of building
- downside risk
- commercial potential`}
                />
              </label>
            </OptionalSection>

            <OptionalSection
              title="Add artifact / plan text"
              explainer="Useful if you want the War Room to pressure-test a draft, plan, pitch, code summary, or concrete proposal."
            >
              <label className="field">
                <span>Artifact / plan text</span>
                <textarea
                  value={candidateOutput}
                  onChange={(e) => setCandidateOutput(e.target.value)}
                  rows={8}
                  placeholder="Paste the plan, draft, proposal, or artifact here."
                />
              </label>
            </OptionalSection>
          </div>
        )}

        {(mode === 'evaluate' || mode === 'critique') && (
          <label className="field">
            <span>{mode === 'evaluate' ? 'Candidate output' : 'Candidate output / artifact'}</span>
            <textarea
              value={candidateOutput}
              onChange={(e) => setCandidateOutput(e.target.value)}
              rows={8}
            />
          </label>
        )}

        {mode === 'compare' && (
          <div className="candidate-list">
            <div className="section-row">
              <h3>Candidates</h3>
              <button type="button" className="secondary-button" onClick={addCandidate}>
                Add candidate
              </button>
            </div>
            {candidates.map((candidate, index) => (
              <div className="candidate-editor" key={index}>
                <div className="candidate-grid">
                  <label className="field">
                    <span>ID</span>
                    <input
                      value={candidate.id}
                      onChange={(e) => updateCandidate(index, 'id', e.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span>Title</span>
                    <input
                      value={candidate.title}
                      onChange={(e) => updateCandidate(index, 'title', e.target.value)}
                    />
                  </label>
                </div>
                <label className="field">
                  <span>Content</span>
                  <textarea
                    value={candidate.content}
                    onChange={(e) => updateCandidate(index, 'content', e.target.value)}
                    rows={5}
                  />
                </label>
                {candidates.length > 2 && (
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => removeCandidate(index)}
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {mode !== 'decide' && mode !== 'war_room' && (
          <label className="field">
            <span>Criteria</span>
            <textarea
              value={criteria}
              onChange={(e) => setCriteria(e.target.value)}
              rows={3}
              placeholder="correctness, specificity, usefulness"
            />
          </label>
        )}

        {mode === 'decide' && (
          <>
            <label className="field">
              <span>source_run_id</span>
              <input value={sourceRunId} onChange={(e) => setSourceRunId(e.target.value)} />
            </label>
            <label className="field">
              <span>Thresholds JSON</span>
              <textarea
                value={thresholdsJson}
                onChange={(e) => setThresholdsJson(e.target.value)}
                rows={6}
              />
            </label>
            <label className="field">
              <span>Rules JSON</span>
              <textarea value={rulesJson} onChange={(e) => setRulesJson(e.target.value)} rows={5} />
            </label>
          </>
        )}

        {error && <div className="workbench-error">{error}</div>}

        <button className="run-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? 'Running...' : mode === 'war_room' ? 'Run War Room' : `Run ${mode}`}
        </button>
      </form>

      <CaseResult result={result} />
    </div>
  );
}

function OptionalSection({ title, explainer, children }) {
  return (
    <details className="optional-section">
      <summary>{title}</summary>
      <p>{explainer}</p>
      {children}
    </details>
  );
}

function CaseResult({ result }) {
  if (!result) return null;
  const items = resultItems(result);
  const synthesis = synthesisText(result);
  const decision = decisionText(result);
  const verdict = verdictText(result);
  const firstAction = oneThingToDoFirst(verdict);
  const path = artifactPath(result);

  return (
    <div className="case-result">
      <div className="result-header">
        <div>
          <span className="result-label">run_id</span>
          <strong>{result.run_id}</strong>
        </div>
        <div>
          <span className="result-label">status</span>
          <strong>{result.status || 'completed'}</strong>
        </div>
      </div>

      {path && (
        <div className="artifact-path">
          <span className="result-label">artifact</span>
          <code>{path}</code>
        </div>
      )}

      {result.framed_question && (
        <section className="result-section">
          <h3>Framed Question</h3>
          <div className="markdown-content">
            <ReactMarkdown>{result.framed_question}</ReactMarkdown>
          </div>
        </section>
      )}

      {(verdict || decision || synthesis) && (
        <section className={`result-section ${verdict ? 'verdict-section' : ''}`}>
          <h3>{verdict ? 'Final Verdict' : decision ? 'Decision' : 'Synthesis'}</h3>
          {result.verdict && <ModelIdentity item={result.verdict} />}
          {firstAction && (
            <div className="first-action">
              <span className="result-label">one thing to do first</span>
              <ReactMarkdown>{firstAction}</ReactMarkdown>
            </div>
          )}
          <div className="markdown-content">
            <ReactMarkdown>{verdict || decision || synthesis}</ReactMarkdown>
          </div>
        </section>
      )}

      {result.aggregate_rankings && result.aggregate_rankings.length > 0 && (
        <section className="result-section">
          <h3>Aggregate Rankings</h3>
          <pre className="json-block">{JSON.stringify(result.aggregate_rankings, null, 2)}</pre>
        </section>
      )}

      {items.length > 0 && (
        <section className="result-section">
          <h3>{result.advisor_responses ? 'Advisor Responses' : 'Independent Outputs'}</h3>
          {items.map((item, index) => (
            <details className="result-details" key={item.id || index}>
              <summary>{itemTitle(item, index)}</summary>
              <ModelIdentity item={item} />
              <div className="markdown-content">
                <ReactMarkdown>{itemText(item)}</ReactMarkdown>
              </div>
            </details>
          ))}
        </section>
      )}

      {result.peer_reviews && result.peer_reviews.length > 0 && (
        <section className="result-section">
          <h3>Peer Reviews</h3>
          {result.peer_reviews.map((item, index) => (
            <details className="result-details" key={item.id || index}>
              <summary>{itemTitle(item, index)}</summary>
              <ModelIdentity item={item} />
              <div className="markdown-content">
                <ReactMarkdown>{item.review || item.response || ''}</ReactMarkdown>
              </div>
            </details>
          ))}
        </section>
      )}

      <details className="result-details raw-json">
        <summary>Raw JSON</summary>
        <pre className="json-block">{JSON.stringify(result, null, 2)}</pre>
      </details>
    </div>
  );
}

function ModelIdentity({ item }) {
  const details = modelDetails(item);
  return (
    <div className={`model-identity ${details.fallbackUsed ? 'fallback' : ''}`}>
      <strong>{modelDisplayLabel(item)}</strong>
      <span>Requested alias: {details.requestedAlias || 'unknown'}</span>
      <span>Requested: {details.requested}</span>
      <span>Actual: {details.actual}</span>
      {details.fallbackUsed && (
        <span>Fallback reason: {details.fallbackReason || 'fallback used'}</span>
      )}
    </div>
  );
}
