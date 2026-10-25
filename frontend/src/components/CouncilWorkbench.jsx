import { useCallback, useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from '../api';
import './CouncilWorkbench.css';

const WORKFLOWS = [
  { id: 'ask', label: 'Ask', description: 'Independent answers, review, and synthesis.' },
  { id: 'council', label: 'Council', description: 'Role-based deliberation for hard decisions.' },
  { id: 'compare', label: 'Compare', description: 'Evaluate named options against clear criteria.' },
];

const STAGE_LABELS = {
  independent_responses: 'Independent responses', advisor_responses: 'Council seats',
  comparisons: 'Independent comparisons', peer_review: 'Peer review', synthesis: 'Synthesis',
  verdict: 'Verdict', run: 'Run complete',
};

function clone(value) { return JSON.parse(JSON.stringify(value)); }

function formatDate(value) {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat(undefined, {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(date);
}

function resultText(run) {
  const outputs = run?.outputs || {};
  return outputs.verdict?.response || outputs.verdict?.raw_output ||
    outputs.synthesis?.response || outputs.synthesis?.raw_output ||
    run?.verdict?.response || run?.synthesis?.response || '';
}

function responseItems(run) {
  const outputs = run?.outputs || {};
  return outputs.advisor_responses || outputs.independent_responses || outputs.comparisons ||
    run?.advisor_responses || run?.independent_responses || run?.comparisons || [];
}

function responseText(item) { return item.response || item.comparison || item.raw_output || ''; }
function statusLabel(status) { return status === 'completed' ? 'Complete' : status === 'partial' ? 'Partial' : status; }

function Icon({ name, size = 18 }) {
  const paths = {
    council: <><circle cx="7" cy="8" r="3"/><circle cx="17" cy="8" r="3"/><path d="M2 21c0-4 2-7 5-7s5 3 5 7M12 21c0-4 2-7 5-7s5 3 5 7"/></>,
    plus: <path d="M12 5v14M5 12h14"/>,
    history: <><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/></>,
    spark: <><path d="m12 3 1.4 4.1L17.5 8.5l-4.1 1.4L12 14l-1.4-4.1-4.1-1.4 4.1-1.4L12 3Z"/><path d="m19 15 .8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8L19 15Z"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>, check: <path d="m5 12 4 4L19 6"/>,
    alert: <><path d="M12 3 2.5 20h19L12 3Z"/><path d="M12 9v4M12 17h.01"/></>,
    chevron: <path d="m9 18 6-6-6-6"/>, close: <path d="m6 6 12 12M18 6 6 18"/>,
  };
  return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

export default function CouncilWorkbench() {
  const [providers, setProviders] = useState({ aliases: [], ready_aliases: [] });
  const [presets, setPresets] = useState([]);
  const [runs, setRuns] = useState([]);
  const [workflow, setWorkflow] = useState('council');
  const [draftPreset, setDraftPreset] = useState(null);
  const [task, setTask] = useState('');
  const [context, setContext] = useState('');
  const [criteria, setCriteria] = useState('');
  const [candidates, setCandidates] = useState([
    { id: 'option-a', title: '', content: '' }, { id: 'option-b', title: '', content: '' },
  ]);
  const [activeRun, setActiveRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [inspectorOpen, setInspectorOpen] = useState(() => window.innerWidth > 1120);

  const loadWorkspace = useCallback(async () => {
    setLoading(true);
    try {
      const [providerData, presetData, runData] = await Promise.all([
        api.listProviders(), api.listPresets(), api.listRuns(),
      ]);
      setProviders(providerData); setPresets(presetData); setRuns(runData); setError('');
    } catch (err) { setError(err.message || 'Could not load the workbench.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadWorkspace(); }, [loadWorkspace]);

  const workflowPresets = useMemo(
    () => presets.filter((preset) => preset.workflow_type === workflow), [presets, workflow]
  );

  useEffect(() => {
    const preferred = workflowPresets.find((preset) => preset.built_in) || workflowPresets[0];
    setDraftPreset(preferred ? clone(preferred) : null);
  }, [workflow, workflowPresets]);

  const selectWorkflow = (nextWorkflow) => { setWorkflow(nextWorkflow); setActiveRun(null); setError(''); };
  const selectPreset = (presetId) => {
    const preset = presets.find((item) => item.id === presetId);
    if (preset) setDraftPreset(clone(preset));
  };
  const updateSeat = (index, field, value) => setDraftPreset((previous) => ({
    ...previous, seats: previous.seats.map((seat, seatIndex) => seatIndex === index ? { ...seat, [field]: value } : seat),
  }));
  const addSeat = () => setDraftPreset((previous) => ({ ...previous, seats: [...previous.seats, {
    id: `seat-${Date.now()}`, name: 'New seat', role_prompt: 'Examine the problem from a distinct and useful perspective.',
    model_alias: providers.aliases[0]?.alias || '', enabled: true,
  }] }));
  const removeSeat = (index) => {
    if (draftPreset.seats.filter((seat) => seat.enabled).length <= 1) {
      setError('A council needs at least one active seat.'); return;
    }
    setDraftPreset((previous) => ({ ...previous, seats: previous.seats.filter((_, seatIndex) => seatIndex !== index) }));
  };

  const startRun = async (event) => {
    event.preventDefault();
    if (!task.trim() || !draftPreset) return;
    const cleanCandidates = candidates.map((candidate) => ({
      id: candidate.id.trim(), title: candidate.title.trim(), content: candidate.content.trim(),
    }));
    if (workflow === 'compare' && cleanCandidates.some((candidate) => !candidate.id || !candidate.title || !candidate.content)) {
      setError('Every comparison option needs an ID, title, and content.'); return;
    }
    setRunning(true); setActiveRun(null); setError('');
    try {
      const run = await api.createRun({ workflow_type: workflow, task: task.trim(), context: context.trim() || null,
        criteria: criteria.split(/[\n,]/).map((item) => item.trim()).filter(Boolean),
        candidates: workflow === 'compare' ? cleanCandidates : [], preset: { ...draftPreset, built_in: false } });
      setActiveRun(run); setRuns(await api.listRuns());
    } catch (err) { setError(err.message || 'The council run failed.'); }
    finally { setRunning(false); }
  };

  const openRun = async (runId) => {
    try {
      const run = await api.getRun(runId); setActiveRun(run);
      setWorkflow(run.workflow_type || run.case_type || 'council'); setError('');
    } catch (err) {
      setError(err.message || 'Could not reopen this run.');
      setRuns((previous) => previous.filter((run) => run.run_id !== runId));
    }
  };

  const readyAliases = new Set(providers.ready_aliases);
  const selectedWorkflow = WORKFLOWS.find((item) => item.id === workflow);

  return <div className={`council-shell ${inspectorOpen ? '' : 'inspector-collapsed'}`}>
    <aside className="left-rail">
      <div className="brand"><div className="brand-mark"><Icon name="council" size={22}/></div><div><strong>Extended Council</strong><span>Multi-model reasoning</span></div></div>
      <button className="new-run-button" type="button" onClick={() => setActiveRun(null)}><Icon name="plus"/> New run</button>
      <nav className="rail-section" aria-label="Workflows"><div className="rail-label">Workflows</div>
        {WORKFLOWS.map((item) => <button key={item.id} type="button" className={`rail-item ${workflow === item.id && !activeRun ? 'active' : ''}`} onClick={() => selectWorkflow(item.id)}><span>{item.label}</span><span className="rail-count">{presets.filter((preset) => preset.workflow_type === item.id).length}</span></button>)}
      </nav>
      <section className="rail-section run-history"><div className="rail-label"><span>Recent runs</span><Icon name="history" size={15}/></div><div className="run-list">
        {runs.length === 0 && !loading ? <p className="muted-copy">No runs yet.</p> : null}
        {runs.map((run) => <button key={run.run_id} type="button" className={`run-list-item ${activeRun?.run_id === run.run_id ? 'active' : ''}`} onClick={() => openRun(run.run_id)}><span className={`status-dot ${run.status}`}/><span className="run-list-copy"><strong>{run.task || 'Untitled run'}</strong><small>{run.preset_name || run.workflow_type} · {formatDate(run.created_at)}</small></span></button>)}
      </div></section>
      <div className="rail-footer"><span className={`connection-dot ${loading ? 'checking' : error ? 'offline' : 'online'}`}/>{loading ? 'Checking backend…' : error ? 'Backend issue' : 'Local backend connected'}</div>
    </aside>

    <main className="main-canvas">
      <header className="canvas-header"><div><div className="eyebrow">{activeRun ? 'Run record' : 'New deliberation'}</div><h1>{activeRun ? activeRun.input?.task || 'Council result' : selectedWorkflow.label}</h1>{!activeRun && <p>{selectedWorkflow.description}</p>}</div><button className="icon-button inspector-toggle" type="button" onClick={() => setInspectorOpen((value) => !value)} aria-label="Toggle inspector"><Icon name="settings"/></button></header>
      {error && <div className="notice error-notice" role="alert"><Icon name="alert"/><span>{error}</span><button type="button" onClick={() => setError('')} aria-label="Dismiss error"><Icon name="close" size={16}/></button></div>}
      {!activeRun ? <form className="composer" onSubmit={startRun}>
        <div className="workflow-tabs" role="tablist" aria-label="Workflow type">{WORKFLOWS.map((item) => <button key={item.id} type="button" role="tab" aria-selected={workflow === item.id} className={workflow === item.id ? 'active' : ''} onClick={() => selectWorkflow(item.id)}>{item.label}</button>)}</div>
        <label className="task-field"><span>{workflow === 'compare' ? 'What decision should the options resolve?' : workflow === 'council' ? 'What should the council pressure-test?' : 'What do you want the council to answer?'}</span><textarea value={task} onChange={(event) => setTask(event.target.value)} rows="6" placeholder="Describe the decision, question, or plan. Include enough context for a serious answer." required/></label>
        {workflow === 'compare' && <div className="candidate-stack"><div className="section-heading"><div><span className="eyebrow">Options</span><h2>Comparison candidates</h2></div><button className="text-button" type="button" onClick={() => setCandidates((previous) => [...previous, { id: `option-${previous.length + 1}`, title: '', content: '' }])}>+ Add option</button></div>
          {candidates.map((candidate, index) => <div className="candidate-card" key={`${candidate.id}-${index}`}><input aria-label={`Option ${index + 1} ID`} value={candidate.id} onChange={(event) => setCandidates((previous) => previous.map((item, itemIndex) => itemIndex === index ? { ...item, id: event.target.value } : item))} placeholder="option-id"/><input aria-label={`Option ${index + 1} title`} value={candidate.title} onChange={(event) => setCandidates((previous) => previous.map((item, itemIndex) => itemIndex === index ? { ...item, title: event.target.value } : item))} placeholder="Option title"/><textarea aria-label={`Option ${index + 1} content`} value={candidate.content} onChange={(event) => setCandidates((previous) => previous.map((item, itemIndex) => itemIndex === index ? { ...item, content: event.target.value } : item))} placeholder="Describe this option" rows="3"/></div>)}
        </div>}
        <div className="supporting-fields"><label><span>Context <small>optional</small></span><textarea value={context} onChange={(event) => setContext(event.target.value)} rows="3" placeholder="Constraints, background, or relevant facts"/></label><label><span>Criteria <small>one per line</small></span><textarea value={criteria} onChange={(event) => setCriteria(event.target.value)} rows="3" placeholder={'Expected value\nDownside risk\nReversibility'}/></label></div>
        <div className="run-summary"><div className="summary-icon"><Icon name="spark"/></div><div><strong>{draftPreset?.name || 'Select a preset'}</strong><span>{draftPreset?.seats.filter((seat) => seat.enabled).length || 0} active seats · {draftPreset?.synthesizer_alias || 'No synthesizer'}</span></div><button className="primary-button" type="submit" disabled={running || !task.trim() || !draftPreset}>{running ? <><span className="spinner"/> Council running</> : <>Start run <Icon name="arrow"/></>}</button></div>
      </form> : <RunResult run={activeRun} onNewRun={() => setActiveRun(null)}/>} 
    </main>

    <aside className="inspector"><div className="inspector-header"><div><span className="eyebrow">Configuration</span><h2>{activeRun ? 'Run evidence' : 'Council setup'}</h2></div><button className="icon-button" type="button" onClick={() => setInspectorOpen(false)} aria-label="Close inspector"><Icon name="close"/></button></div>
      {activeRun ? <RunInspector run={activeRun}/> : <><label className="select-field"><span>Preset</span><select value={draftPreset?.id || ''} onChange={(event) => selectPreset(event.target.value)}>{workflowPresets.map((preset) => <option value={preset.id} key={preset.id}>{preset.name}</option>)}</select></label>
        {providers.ready_aliases.length === 0 && !loading && <div className="notice provider-notice"><Icon name="alert"/><span>No provider is ready. Configure at least one API key before running.</span></div>}
        <div className="seat-heading"><span>Seats</span><small>Role → model</small></div><div className="seat-list">{draftPreset?.seats.map((seat, index) => <div className="seat-card" key={seat.id}><div className="seat-card-top"><span className="seat-number">{String(index + 1).padStart(2, '0')}</span><input aria-label={`Seat ${index + 1} name`} value={seat.name} onChange={(event) => updateSeat(index, 'name', event.target.value)}/><button type="button" aria-label={`Remove ${seat.name}`} onClick={() => removeSeat(index)}><Icon name="close" size={14}/></button></div><textarea aria-label={`${seat.name} role prompt`} rows="3" value={seat.role_prompt} onChange={(event) => updateSeat(index, 'role_prompt', event.target.value)}/><label className="model-select"><span className={`status-dot ${readyAliases.has(seat.model_alias) ? 'completed' : 'failed'}`}/><select aria-label={`${seat.name} model`} value={seat.model_alias} onChange={(event) => updateSeat(index, 'model_alias', event.target.value)}>{providers.aliases.map((model) => <option value={model.alias} key={model.alias}>{model.display_name} · {model.provider}</option>)}</select></label></div>)}</div>
        <button className="add-seat-button" type="button" onClick={addSeat}><Icon name="plus" size={16}/> Add seat</button><div className="assignment-block"><span>Synthesizer</span><select value={draftPreset?.synthesizer_alias || ''} onChange={(event) => setDraftPreset((previous) => ({ ...previous, synthesizer_alias: event.target.value }))}>{providers.aliases.map((model) => <option value={model.alias} key={model.alias}>{model.display_name}</option>)}</select></div></>}
    </aside>
  </div>;
}

function RunResult({ run, onNewRun }) {
  const finalText = resultText(run); const items = responseItems(run); const events = run.stage_events || [];
  return <div className="run-result"><div className="result-toolbar"><div className={`status-pill ${run.status}`}><span className={`status-dot ${run.status}`}/>{statusLabel(run.status)}</div><span>{formatDate(run.completed_at || run.created_at)}</span><button className="secondary-button" type="button" onClick={onNewRun}><Icon name="plus" size={16}/> New run</button></div>
    <section className="verdict-card"><div className="section-heading"><div><span className="eyebrow">Council synthesis</span><h2>{run.workflow_type === 'compare' ? 'Comparison verdict' : run.workflow_type === 'ask' ? 'Synthesized answer' : 'Council verdict'}</h2></div><Icon name="spark" size={22}/></div>{finalText ? <div className="markdown-content"><ReactMarkdown>{finalText}</ReactMarkdown></div> : <p className="muted-copy">No synthesis was produced. Inspect the errors and individual responses below.</p>}</section>
    <section className="timeline-section"><div className="section-heading"><div><span className="eyebrow">Process</span><h2>Deliberation timeline</h2></div></div><div className="timeline">{events.map((event, index) => <div className="timeline-step" key={`${event.stage}-${index}`}><span className={`timeline-marker ${event.status}`}><Icon name={event.status === 'completed' ? 'check' : event.status === 'running' ? 'spark' : 'alert'} size={14}/></span><div><strong>{STAGE_LABELS[event.stage] || event.stage}</strong><small>{statusLabel(event.status)}</small></div></div>)}</div></section>
    <section className="responses-section"><div className="section-heading"><div><span className="eyebrow">Evidence</span><h2>Individual perspectives</h2></div><span className="count-badge">{items.length}</span></div><div className="response-grid">{items.map((item, index) => <details className="response-card" key={item.id || index}><summary><div><span>{item.advisor_name || item.display_name || `Response ${index + 1}`}</span><small>{item.actual_display_name || item.display_name || item.alias || item.model}</small></div><Icon name="chevron" size={16}/></summary><div className="markdown-content"><ReactMarkdown>{responseText(item)}</ReactMarkdown></div></details>)}</div></section>
    {run.errors?.length > 0 && <section className="error-list"><h2>Run issues</h2>{run.errors.map((item, index) => <p key={index}>{item}</p>)}</section>}
  </div>;
}

function RunInspector({ run }) {
  const preset = run.preset_snapshot || run.input?.preset_snapshot || {};
  const responses = run.provider_metadata?.responses || [];
  const artifacts = run.artifact_paths || {};
  return <div className="run-inspector"><div className="evidence-block"><span>Preset snapshot</span><strong>{preset.name || preset.id || 'Legacy configuration'}</strong><small>{preset.seats?.length || run.input?.respondent_aliases?.length || 0} seats preserved</small></div><div className="seat-heading"><span>Model evidence</span><small>{responses.length} calls</small></div><div className="model-evidence-list">{responses.map((item, index) => <div className="model-evidence" key={`${item.id}-${index}`}><span className={`status-dot ${item.error ? 'failed' : 'completed'}`}/><div><strong>{item.display_name || item.alias || 'Model call'}</strong><small>{item.actual_provider && item.actual_model ? `${item.actual_provider}/${item.actual_model}` : 'No successful provider response'}</small>{item.fallback_used ? <em>Fallback used</em> : null}</div></div>)}</div><div className="seat-heading"><span>Artifacts</span></div>{Object.entries(artifacts).map(([name, path]) => <div className="artifact-row" key={name}><span>{name.replaceAll('_', ' ')}</span><code title={path}>{path}</code></div>)}</div>;
}
