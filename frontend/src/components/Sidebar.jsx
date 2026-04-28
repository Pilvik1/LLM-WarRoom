import { useState, useEffect } from 'react';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
}) {
  const handleDelete = (event, conversationId) => {
    event.stopPropagation();
    const confirmed = window.confirm('Delete this conversation? This cannot be undone.');
    if (confirmed) {
      onDeleteConversation(conversationId);
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>WarRoom</h1>
        <button className="new-conversation-btn" onClick={onNewConversation}>
          + New Conversation
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No conversations yet</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-content">
                <div className="conversation-title">
                  {conv.title || 'New Conversation'}
                </div>
                <div className="conversation-meta">
                  {conv.message_count} messages
                </div>
              </div>
              <button
                type="button"
                className="delete-conversation-btn"
                aria-label={`Delete ${conv.title || 'conversation'}`}
                title="Delete conversation"
                onClick={(event) => handleDelete(event, conv.id)}
              >
                ×
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
