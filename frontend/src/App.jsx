import { useCallback, useEffect, useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import CaseWorkbench from './components/CaseWorkbench';
import { api } from './api';
import './App.css';

function App() {
  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [mode, setMode] = useState('ask');
  const [appError, setAppError] = useState('');

  const loadConversations = useCallback(async () => {
    try {
      const convs = await api.listConversations();
      setConversations(convs);
      setAppError('');
    } catch (error) {
      setAppError(error.message || 'Failed to load conversations.');
    }
  }, []);

  const loadConversation = useCallback(async (id) => {
    try {
      const conv = await api.getConversation(id);
      setCurrentConversation(conv);
      setAppError('');
    } catch (error) {
      if (error.status === 404) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
        await loadConversations();
      }
      setAppError(error.message || 'Failed to load conversation.');
    }
  }, [loadConversations]);

  // Load conversations on mount
  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId, loadConversation]);

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation();
      setMode('ask');
      setConversations((previous) => [
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...previous,
      ]);
      setCurrentConversation(newConv);
      setCurrentConversationId(newConv.id);
      setAppError('');
    } catch (error) {
      setAppError(error.message || 'Failed to create conversation.');
    }
  };

  const handleSelectConversation = (id) => {
    setMode('ask');
    setCurrentConversationId(id);
  };

  const handleDeleteConversation = async (id) => {
    try {
      await api.deleteConversation(id);
      setConversations((prev) => prev.filter((conversation) => conversation.id !== id));
      if (id === currentConversationId) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
        setMode('ask');
        setIsLoading(false);
      }
    } catch (error) {
      setAppError(error.message || 'Failed to delete conversation.');
    }
  };

  const handleSendMessage = async (content) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    setAppError('');
    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        metadata: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming
      await api.sendMessageStream(currentConversationId, content, (eventType, event) => {
        const updateLastAssistant = (updater) => {
          setCurrentConversation((previous) => {
            const messages = previous.messages.map((message, index) =>
              index === previous.messages.length - 1
                ? updater(message)
                : message
            );
            return { ...previous, messages };
          });
        };

        switch (eventType) {
          case 'stage1_start':
            updateLastAssistant((message) => ({
              ...message,
              run_id: event.run_id || message.run_id,
              loading: { ...message.loading, stage1: true },
            }));
            break;

          case 'run_start':
            updateLastAssistant((message) => ({
              ...message,
              run_id: event.run_id,
              case_type: event.case_type,
            }));
            break;

          case 'stage1_complete':
            updateLastAssistant((message) => ({
              ...message,
              run_id: event.run_id || message.run_id,
              stage1: event.data,
              loading: { ...message.loading, stage1: false },
            }));
            break;

          case 'stage2_start':
            updateLastAssistant((message) => ({
              ...message,
              loading: { ...message.loading, stage2: true },
            }));
            break;

          case 'stage2_complete':
            updateLastAssistant((message) => ({
              ...message,
              run_id: event.run_id || message.run_id,
              stage2: event.data,
              metadata: event.metadata,
              loading: { ...message.loading, stage2: false },
            }));
            break;

          case 'stage3_start':
            updateLastAssistant((message) => ({
              ...message,
              loading: { ...message.loading, stage3: true },
            }));
            break;

          case 'stage3_complete':
            updateLastAssistant((message) => ({
              ...message,
              run_id: event.run_id || message.run_id,
              stage3: event.data,
              loading: { ...message.loading, stage3: false },
            }));
            break;

          case 'title_complete':
            // Reload conversations to get updated title
            loadConversations();
            break;

          case 'complete':
            // Stream complete, reload conversations list
            loadConversations();
            setIsLoading(false);
            break;

          case 'error':
            updateLastAssistant((message) => ({
              ...message,
              error: event.message || 'The council run failed.',
              loading: { stage1: false, stage2: false, stage3: false },
            }));
            setAppError(event.message || 'The council run failed.');
            setIsLoading(false);
            break;

          default:
            break;
        }
      });
    } catch (error) {
      setAppError(error.message || 'Failed to send message.');
      setCurrentConversation((previous) => ({
        ...previous,
        messages: previous.messages.map((message, index) =>
          index === previous.messages.length - 1
            ? {
                ...message,
                error: error.message || 'Failed to send message.',
                loading: { stage1: false, stage2: false, stage3: false },
              }
            : message
        ),
      }));
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
      />
      {mode === 'ask' ? (
        <ChatInterface
          conversation={currentConversation}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          error={appError}
          onDismissError={() => setAppError('')}
          mode={mode}
          onModeChange={setMode}
        />
      ) : (
        <CaseWorkbench mode={mode} onModeChange={setMode} />
      )}
    </div>
  );
}

export default App;
