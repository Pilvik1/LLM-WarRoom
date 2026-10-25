import { describe, expect, it, vi } from 'vitest';
import { consumeSseBuffer } from './api';

describe('consumeSseBuffer', () => {
  it('buffers an event split across transport reads', () => {
    const onEvent = vi.fn();
    let buffer = consumeSseBuffer('data: {"type":"stage1_', onEvent);
    expect(onEvent).not.toHaveBeenCalled();

    buffer = consumeSseBuffer(
      `${buffer}complete","data":[1]}\n\n`,
      onEvent
    );

    expect(buffer).toBe('');
    expect(onEvent).toHaveBeenCalledWith('stage1_complete', {
      type: 'stage1_complete',
      data: [1],
    });
  });

  it('dispatches multiple complete events and preserves the partial tail', () => {
    const onEvent = vi.fn();
    const buffer = consumeSseBuffer(
      'data: {"type":"one"}\n\ndata: {"type":"two"}\n\ndata: {"type":',
      onEvent
    );

    expect(onEvent).toHaveBeenCalledTimes(2);
    expect(buffer).toBe('data: {"type":');
  });
});
