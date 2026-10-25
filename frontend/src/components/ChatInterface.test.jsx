import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ChatInterface from './ChatInterface';

describe('ChatInterface', () => {
  it('keeps the composer available after the first response', () => {
    render(
      <ChatInterface
        conversation={{
          id: 'conversation-1',
          messages: [
            { role: 'user', content: 'First question' },
            {
              role: 'assistant',
              stage1: [],
              stage2: [],
              stage3: { response: 'First answer', metadata: {} },
            },
          ],
        }}
        onSendMessage={vi.fn()}
        isLoading={false}
        error=""
        onDismissError={vi.fn()}
        mode="ask"
        onModeChange={vi.fn()}
      />
    );

    expect(screen.getByLabelText('Council question')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument();
  });
});
