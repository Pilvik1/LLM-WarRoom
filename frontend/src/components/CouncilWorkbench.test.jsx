import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import CouncilWorkbench from './CouncilWorkbench';

const providers = {
  aliases: [
    { alias: 'model-a', provider: 'openai', display_name: 'Model A', enabled: true },
    { alias: 'model-b', provider: 'anthropic', display_name: 'Model B', enabled: false },
  ],
  ready_aliases: ['model-a'],
};

const presets = [
  {
    id: 'general-council',
    name: 'General Council',
    workflow_type: 'council',
    built_in: true,
    reviewer_aliases: ['model-a'],
    synthesizer_alias: 'model-a',
    seats: [
      { id: 'skeptic', name: 'Skeptic', role_prompt: 'Challenge assumptions.', model_alias: 'model-b', enabled: true },
    ],
  },
  {
    id: 'multi-model-ask',
    name: 'Multi-model Ask',
    workflow_type: 'ask',
    built_in: true,
    reviewer_aliases: ['model-a'],
    synthesizer_alias: 'model-a',
    seats: [
      { id: 'answerer', name: 'Answerer', role_prompt: 'Answer independently.', model_alias: 'model-a', enabled: true },
    ],
  },
];

function jsonResponse(body, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  }));
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('CouncilWorkbench', () => {
  it('loads presets and exposes editable role-to-model assignments', async () => {
    vi.stubGlobal('fetch', vi.fn((url) => {
      if (url.endsWith('/api/providers')) return jsonResponse(providers);
      if (url.endsWith('/api/presets')) return jsonResponse(presets);
      if (url.endsWith('/api/runs')) return jsonResponse([]);
      throw new Error(`Unexpected URL: ${url}`);
    }));

    render(<CouncilWorkbench />);

    expect(await screen.findByLabelText('Seat 1 name')).toHaveValue('Skeptic');
    expect(screen.getByLabelText('Skeptic model')).toHaveValue('model-b');

    fireEvent.change(screen.getByLabelText('Skeptic model'), { target: { value: 'model-a' } });
    expect(screen.getByLabelText('Skeptic model')).toHaveValue('model-a');
  });

  it('creates a canonical run from the selected workflow and preset snapshot', async () => {
    const fetchMock = vi.fn((url, options = {}) => {
      if (url.endsWith('/api/providers')) return jsonResponse(providers);
      if (url.endsWith('/api/presets')) return jsonResponse(presets);
      if (url.endsWith('/api/runs') && !options.method) return jsonResponse([]);
      if (url.endsWith('/api/runs') && options.method === 'POST') {
        return jsonResponse({
          run_id: 'run-1', workflow_type: 'council', status: 'completed',
          input: { task: 'Should we ship?' }, stage_events: [], outputs: {}, errors: [],
        }, 201);
      }
      throw new Error(`Unexpected URL: ${url}`);
    });
    vi.stubGlobal('fetch', fetchMock);
    render(<CouncilWorkbench />);

    await screen.findByLabelText('Seat 1 name');
    fireEvent.change(screen.getByPlaceholderText(/Describe the decision/), { target: { value: 'Should we ship?' } });
    fireEvent.click(screen.getByRole('button', { name: /Start run/ }));

    await screen.findByText('Should we ship?');
    const request = fetchMock.mock.calls.find(([, options]) => options?.method === 'POST');
    const payload = JSON.parse(request[1].body);
    expect(payload.workflow_type).toBe('council');
    expect(payload.preset.seats[0].model_alias).toBe('model-b');
    await waitFor(() => expect(screen.getByText('Complete')).toBeInTheDocument());
  });
});
