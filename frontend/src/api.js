/**
 * API client for the WarRoom backend.
 */

const API_BASE = 'http://localhost:8001';

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
  throw new Error(detail || fallbackMessage);
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

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
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
