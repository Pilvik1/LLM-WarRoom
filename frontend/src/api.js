/** API client for the council backend. */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8001';

async function parseResponse(response, fallbackMessage) {
  if (response.ok) {
    return response.json();
  }

  let detail = fallbackMessage;
  try {
    const errorBody = await response.json();
    detail = errorBody.detail || errorBody.message || JSON.stringify(errorBody);
  } catch {
    detail = await response.text();
  }
  const error = new Error(detail || fallbackMessage);
  error.status = response.status;
  throw error;
}

function dispatchSseFrame(frame, onEvent) {
  const data = frame
    .split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trimStart())
    .join('\n');

  if (!data) return;
  const event = JSON.parse(data);
  onEvent(event.type, event);
}

export function consumeSseBuffer(buffer, onEvent, flush = false) {
  let remaining = buffer;
  let match = remaining.match(/\r?\n\r?\n/);

  while (match) {
    const frame = remaining.slice(0, match.index);
    remaining = remaining.slice(match.index + match[0].length);
    if (frame.trim()) dispatchSseFrame(frame, onEvent);
    match = remaining.match(/\r?\n\r?\n/);
  }

  if (flush && remaining.trim()) {
    dispatchSseFrame(remaining, onEvent);
    return '';
  }
  return remaining;
}

export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    return parseResponse(response, 'Failed to list conversations');
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    return parseResponse(response, 'Failed to create conversation');
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    return parseResponse(response, 'Failed to get conversation');
  },

  async deleteConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`,
      {
        method: 'DELETE',
      }
    );
    return parseResponse(response, 'Failed to delete conversation');
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );
    return parseResponse(response, 'Failed to send message');
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      await parseResponse(response, 'Failed to send message');
    }

    if (!response.body) {
      throw new Error('The server returned an empty event stream.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      buffer = consumeSseBuffer(buffer, onEvent);
    }

    buffer += decoder.decode();
    consumeSseBuffer(buffer, onEvent, true);
  },

  async evaluateCase(payload) {
    const response = await fetch(`${API_BASE}/api/cases/evaluate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseResponse(response, 'Failed to run evaluate case');
  },

  async critiqueCase(payload) {
    const response = await fetch(`${API_BASE}/api/cases/critique`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseResponse(response, 'Failed to run critique case');
  },

  async compareCase(payload) {
    const response = await fetch(`${API_BASE}/api/cases/compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseResponse(response, 'Failed to run compare case');
  },

  async decideCase(payload) {
    const response = await fetch(`${API_BASE}/api/cases/decide`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseResponse(response, 'Failed to run decide case');
  },

  async warRoomCase(payload) {
    const response = await fetch(`${API_BASE}/api/cases/war-room`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return parseResponse(response, 'Failed to run War Room case');
  },
};
