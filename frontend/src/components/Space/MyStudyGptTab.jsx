import React, { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Send, Bot, User, Paperclip, X, Settings, ChevronDown, ChevronUp,
  Plus, MessageSquare, Pencil, Trash2, Check, Sparkles, AlertTriangle
} from 'lucide-react';
import './LearnTab.css';

// ── TNPSC under-development guard ─────────────────────────────────────────────
function TnpscComingSoon({ subject }) {
  return (
    <div className="tnpsc-coming-soon animate-fade-in">
      <div className="tnpsc-icon">🏛️</div>
      <h2>Dear Aspirant!</h2>
      <p>
        The <strong>TNPSC — {subject}</strong> module is currently under development
        and will be released very soon. Our team is working hard to bring you a
        comprehensive, high-quality learning experience tailored specifically for
        Tamil Nadu Civil Services aspirants.
      </p>
      <p className="tnpsc-sub">
        In the meantime, please stay motivated and keep revising your notes.
        We appreciate your patience and trust in <strong>Vinaval AI</strong>. 🙏
      </p>
      <div className="tnpsc-badge">Coming Soon ✨</div>
    </div>
  );
}

// ── Session sidebar item ───────────────────────────────────────────────────────
function SessionItem({ session, isActive, onSelect, onRename, onDelete }) {
  const [editing, setEditing] = useState(false);
  const [editVal, setEditVal] = useState(session.name);
  const inputRef = useRef(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const commitRename = () => {
    const trimmed = editVal.trim();
    if (trimmed && trimmed !== session.name) onRename(session.id, trimmed);
    setEditing(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') commitRename();
    if (e.key === 'Escape') { setEditVal(session.name); setEditing(false); }
  };

  return (
    <div
      className={`session-item ${isActive ? 'active' : ''}`}
      onClick={() => !editing && onSelect(session.id)}
    >
      <MessageSquare size={14} className="session-icon" />
      {editing ? (
        <input
          ref={inputRef}
          className="session-edit-input"
          value={editVal}
          onChange={e => setEditVal(e.target.value)}
          onBlur={commitRename}
          onKeyDown={handleKeyDown}
          onClick={e => e.stopPropagation()}
        />
      ) : (
        <span className="session-name" title={session.name}>{session.name}</span>
      )}
      {isActive && !editing && (
        <div className="session-actions" onClick={e => e.stopPropagation()}>
          <button className="session-btn" title="Rename" onClick={() => { setEditVal(session.name); setEditing(true); }}>
            <Pencil size={12} />
          </button>
          <button className="session-btn danger" title="Delete" onClick={() => onDelete(session.id)}>
            <Trash2 size={12} />
          </button>
        </div>
      )}
    </div>
  );
}

// ── Name suggestion banner ─────────────────────────────────────────────────────
function AiNameSuggestion({ suggestion, onAccept, onDismiss }) {
  if (!suggestion) return null;
  return (
    <div className="ai-name-suggestion animate-fade-in">
      <Sparkles size={14} />
      <span>AI suggests: <strong>"{suggestion}"</strong></span>
      <button className="btn-accept-name" onClick={onAccept}><Check size={12} /> Use it</button>
      <button className="btn-dismiss-name" onClick={onDismiss}><X size={12} /></button>
    </div>
  );
}

// ── Main LearnTab ──────────────────────────────────────────────────────────────
export default function MyStudyGptTab({ spaceId, space }) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [canContinue, setCanContinue] = useState(false);
  const [showOptions, setShowOptions] = useState(false);
  const [chatLang, setChatLang] = useState('auto');
  const [aiSuggestion, setAiSuggestion] = useState(null);  // pending AI name suggestion
  const [newChatName, setNewChatName] = useState('');       // typed name for new chat dialog
  const [showNewChatDialog, setShowNewChatDialog] = useState(false);
  const newChatInputRef = useRef(null);
  const chatEndRef = useRef(null);

  const [activeDoc, setActiveDoc] = useState(() => {
    const saved = sessionStorage.getItem(`activeDoc_${spaceId}`);
    return saved ? JSON.parse(saved) : null;
  });

  // Sync activeDoc
  useEffect(() => {
    if (activeDoc) sessionStorage.setItem(`activeDoc_${spaceId}`, JSON.stringify(activeDoc));
    else sessionStorage.removeItem(`activeDoc_${spaceId}`);
  }, [activeDoc, spaceId]);

  // Listen for active-doc events from Materials tab
  useEffect(() => {
    const handler = (e) => {
      if (e.detail?.spaceId === spaceId) setActiveDoc(e.detail.doc);
    };
    window.addEventListener('set-active-doc', handler);
    return () => window.removeEventListener('set-active-doc', handler);
  }, [spaceId]);

  // Focus new-chat input when dialog opens
  useEffect(() => {
    if (showNewChatDialog) setTimeout(() => newChatInputRef.current?.focus(), 50);
  }, [showNewChatDialog]);

  // Load all chat sessions for this space
  const loadSessions = useCallback(async () => {
    try {
      const data = await api.get(`/spaces/${spaceId}/chat-sessions`);
      setSessions(data || []);
      // Auto-select the most recent session if none active
      if (data?.length > 0 && !activeSessionId) {
        setActiveSessionId(data[data.length - 1].id);
      }
    } catch (err) {
      console.error('Failed to load chat sessions:', err);
    }
  }, [spaceId, activeSessionId]);

  useEffect(() => { loadSessions(); }, [loadSessions]);

  // Load messages for the active session
  useEffect(() => {
    if (!activeSessionId) return;
    const loadMessages = async () => {
      try {
        const history = await api.get(`/spaces/${spaceId}/messages?session_id=${activeSessionId}`);
        setMessages((history || []).map(m => ({ role: m.role, content: m.content })));
      } catch (err) {
        console.error('Failed to load messages:', err);
      }
    };
    loadMessages();
    // Check if this session has a pending AI suggestion
    const s = sessions.find(s => s.id === activeSessionId);
    if (s?.ai_suggested_name && s.name === 'New Chat') {
      setAiSuggestion(s.ai_suggested_name);
    } else {
      setAiSuggestion(null);
    }
  }, [activeSessionId, spaceId, sessions]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // ── Create new chat session ──────────────────────────────────────────────────
  const createSession = async (name) => {
    try {
      const session = await api.post(`/spaces/${spaceId}/chat-sessions`, { name: name || 'New Chat' });
      setSessions(prev => [...prev, session]);
      setActiveSessionId(session.id);
      setMessages([]);
      setAiSuggestion(null);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const handleNewChat = () => {
    setNewChatName('');
    setShowNewChatDialog(true);
  };

  const handleNewChatConfirm = async () => {
    const name = newChatName.trim() || 'New Chat';
    setShowNewChatDialog(false);
    await createSession(name);
  };

  // ── Rename session ──────────────────────────────────────────────────────────
  const handleRename = async (sessionId, newName) => {
    try {
      const updated = await api.put(`/spaces/${spaceId}/chat-sessions/${sessionId}`, { name: newName });
      setSessions(prev => prev.map(s => s.id === sessionId ? updated : s));
      setAiSuggestion(null);  // user has taken control of the name
    } catch (err) {
      console.error('Failed to rename session:', err);
    }
  };

  // ── Accept AI suggestion ────────────────────────────────────────────────────
  const handleAcceptSuggestion = async () => {
    if (!aiSuggestion || !activeSessionId) return;
    await handleRename(activeSessionId, aiSuggestion);
    setAiSuggestion(null);
  };

  // ── Delete session ──────────────────────────────────────────────────────────
  const handleDelete = async (sessionId) => {
    if (!window.confirm('Delete this chat? This cannot be undone.')) return;
    try {
      await api.delete(`/spaces/${spaceId}/chat-sessions/${sessionId}`);
      const remaining = sessions.filter(s => s.id !== sessionId);
      setSessions(remaining);
      if (activeSessionId === sessionId) {
        setActiveSessionId(remaining.length > 0 ? remaining[remaining.length - 1].id : null);
        setMessages([]);
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  // ── Select session ──────────────────────────────────────────────────────────
  const handleSelectSession = (sessionId) => {
    if (sessionId !== activeSessionId) {
      setActiveSessionId(sessionId);
      setCanContinue(false);
    }
  };

  // ── Send message ────────────────────────────────────────────────────────────
  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    if (!activeSessionId) {
      // Auto-create a session if none exists
      await createSession('New Chat');
      return;
    }

    const userMessage = input.trim();
    setInput('');
    setCanContinue(false);
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);
    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    const payload = {
      content: userMessage,
      lang: chatLang,
      chat_session_id: activeSessionId,
      mode: 'my_study_gpt',
    };
    if (activeDoc) {
      payload.active_doc_id = activeDoc.id;
      payload.active_doc_filename = activeDoc.filename;
    }

    try {
      const generator = api.streamPost(`/spaces/${spaceId}/chat`, payload);
      let fullResponse = '';
      for await (const chunk of generator) {
        fullResponse += chunk;
        
        let displayResponse = fullResponse;
        if (displayResponse.includes('[CONTINUE_AVAILABLE]')) {
          setCanContinue(true);
          displayResponse = displayResponse.replace('[CONTINUE_AVAILABLE]', '');
        }

        setMessages(prev => {
          const msgs = [...prev];
          msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content: displayResponse };
          return msgs;
        });
      }

      // After first exchange: poll for AI name suggestion (after short delay for backend)
      if (messages.length === 0) {
        setTimeout(async () => {
          try {
            const refreshed = await api.get(`/spaces/${spaceId}/chat-sessions`);
            setSessions(refreshed || []);
            const updated = (refreshed || []).find(s => s.id === activeSessionId);
            if (updated?.ai_suggested_name && updated.name === 'New Chat') {
              setAiSuggestion(updated.ai_suggested_name);
            }
          } catch (_) {}
        }, 1500);
      }
    } catch (err) {
      setMessages(prev => {
        const msgs = [...prev];
        msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content: `❌ Error: ${err.message}` };
        return msgs;
      });
    } finally {
      setIsLoading(false);
    }
  };

  // ── Continue Generation ───────────────────────────────────────────────────────
  const handleContinue = async () => {
    if (isLoading || !activeSessionId) return;
    setCanContinue(false);
    setIsLoading(true);

    const payload = {
      content: "NEXT",
      lang: chatLang,
      chat_session_id: activeSessionId,
      is_continuation: true,
      mode: 'my_study_gpt',
    };
    if (activeDoc) {
      payload.active_doc_id = activeDoc.id;
      payload.active_doc_filename = activeDoc.filename;
    }

    try {
      const generator = api.streamPost(`/spaces/${spaceId}/chat`, payload);
      let currentContent = messages[messages.length - 1].content;
      let newChunkResponse = '';
      
      for await (const chunk of generator) {
        newChunkResponse += chunk;
        
        // Using regex to remove multiple tags if any, but replace is fine
        let displayResponse = currentContent + '\n\n' + newChunkResponse;
        if (displayResponse.includes('[CONTINUE_AVAILABLE]')) {
          setCanContinue(true);
          displayResponse = displayResponse.replace('[CONTINUE_AVAILABLE]', '');
        }

        setMessages(prev => {
          const msgs = [...prev];
          msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content: displayResponse };
          return msgs;
        });
      }
    } catch (err) {
      setMessages(prev => {
        const msgs = [...prev];
        msgs[msgs.length - 1] = { ...msgs[msgs.length - 1], content: msgs[msgs.length - 1].content + `\n\n❌ Error: ${err.message}` };
        return msgs;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const activeSession = sessions.find(s => s.id === activeSessionId);

  // TNPSC guard — show coming-soon message
  if (space?.exam_id === 'TNPSC') {
    return <TnpscComingSoon subject={space.subject} />;
  }

  return (
    <div className="learn-tab-root animate-fade-in">

      {/* ── Left sidebar: chat sessions ─────────────────────────── */}
      <aside className="chat-sidebar">
        <div className="chat-sidebar-header">
          <span className="chat-sidebar-title">Chats</span>
          <button className="btn-new-chat" onClick={handleNewChat} title="New Chat">
            <Plus size={16} />
          </button>
        </div>

        <div className="sessions-list">
          {sessions.length === 0 ? (
            <div className="sessions-empty">
              <MessageSquare size={28} />
              <p>No chats yet.<br />Start one!</p>
            </div>
          ) : (
            sessions.slice().reverse().map(s => (
              <SessionItem
                key={s.id}
                session={s}
                isActive={s.id === activeSessionId}
                onSelect={handleSelectSession}
                onRename={handleRename}
                onDelete={handleDelete}
              />
            ))
          )}
        </div>
      </aside>

      {/* ── New chat name dialog ────────────────────────────────── */}
      {showNewChatDialog && (
        <div className="modal-overlay" onClick={() => setShowNewChatDialog(false)}>
          <div className="new-chat-dialog animate-fade-in" onClick={e => e.stopPropagation()}>
            <h3><Plus size={18} /> New Chat</h3>
            <p>Give your chat a name, or leave blank for "New Chat".</p>
            <input
              ref={newChatInputRef}
              className="new-chat-input"
              placeholder="e.g. Thermodynamics Doubts..."
              value={newChatName}
              onChange={e => setNewChatName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleNewChatConfirm(); if (e.key === 'Escape') setShowNewChatDialog(false); }}
              maxLength={60}
            />
            <div className="new-chat-actions">
              <button className="btn-secondary" onClick={() => setShowNewChatDialog(false)}>Cancel</button>
              <button className="btn-primary" onClick={handleNewChatConfirm}>
                <Plus size={14} /> Create Chat
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Main chat area ──────────────────────────────────────── */}
      <div className="learn-tab-main">
        {/* Header */}
        <div className="learn-header">
          <div className="learn-header-left">
            <Bot size={22} />
            <div>
              <h2>{activeSession ? activeSession.name : 'My Study GPT'}</h2>
              <p>Ask anything about your uploaded {space?.subject} materials.</p>
            </div>
          </div>
          <button className="btn-new-chat-top" onClick={handleNewChat} title="New Chat">
            <Plus size={15} /> New Chat
          </button>
        </div>

        {/* AI name suggestion banner */}
        {aiSuggestion && (
          <AiNameSuggestion
            suggestion={aiSuggestion}
            onAccept={handleAcceptSuggestion}
            onDismiss={() => setAiSuggestion(null)}
          />
        )}

        {/* Active doc banner */}
        {activeDoc ? (
          <div className="active-doc-banner animate-fade-in">
            <div className="doc-info">
              <Paperclip size={18} className="brand-icon" />
              <div className="doc-info-text">
                <strong>Source: {activeDoc.filename}</strong>
                {activeDoc.topics?.length > 0 && (
                  <span>Topics: {activeDoc.topics.slice(0, 3).join(', ')}{activeDoc.topics.length > 3 ? '...' : ''}</span>
                )}
              </div>
            </div>
            <button className="btn-remove-doc" onClick={() => setActiveDoc(null)}>
              <X size={14} /> Remove
            </button>
          </div>
        ) : (
          <p className="syllabus-note">
            📚 <strong>My Study GPT:</strong> Answers will ONLY be generated from your uploaded materials in the Materials tab.
          </p>
        )}

        {/* Options */}
        <div className="options-expander">
          <div className="options-header" onClick={() => setShowOptions(!showOptions)}>
            <Settings size={14} /> Options {showOptions ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>
          {showOptions && (
            <div className="options-content animate-fade-in">
              <div className="lang-select">
                <label>AI Reply Language</label>
                <select value={chatLang} onChange={e => setChatLang(e.target.value)}>
                  <option value="auto">🤖 Auto-Detect</option>
                  <option value="en">🇬🇧 English</option>
                  <option value="ta">🇮🇳 Tamil</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* No session yet */}
        {!activeSessionId ? (
          <div className="no-session-state">
            <Bot size={48} />
            <h3>Start a Conversation</h3>
            <p>Click <strong>New Chat</strong> to begin a session, or select one from the sidebar.</p>
            <button className="btn-primary" onClick={handleNewChat}>
              <Plus size={16} /> New Chat
            </button>
          </div>
        ) : (
          <>
            {/* Messages */}
            <div className="chat-container">
              {messages.length === 0 && !isLoading && (
                <div className="empty-state" style={{ padding: '2rem', marginTop: '2rem' }}>
                  <Bot size={40} style={{ color: 'var(--text-muted)', margin: '0 auto 1rem' }} />
                  <p>How can I help you study today?</p>
                </div>
              )}
              {messages.map((msg, idx) => (
                <div key={idx} className={`message ${msg.role} animate-fade-in`}>
                  <div className={`avatar ${msg.role}`}>
                    {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
                  </div>
                  <div className="message-content">
                    {msg.role === 'user' ? (
                      <p style={{ margin: 0 }}>{msg.content}</p>
                    ) : (
                      msg.content ? (
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                      ) : (
                        <div className="typing-indicator">
                          <span></span><span></span><span></span>
                        </div>
                      )
                    )}
                  </div>
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>

            {/* Input */}
            <div className="chat-input-wrapper">
              {canContinue && (
                <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '1rem' }}>
                  <button className="btn-primary" onClick={handleContinue} disabled={isLoading} style={{ borderRadius: '20px', padding: '8px 24px' }}>
                    Continue →
                  </button>
                </div>
              )}
              <div className="chat-input-container">
                <textarea
                  placeholder={activeDoc ? `Ask about '${activeDoc.filename}'...` : 'Ask My Study GPT...'}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading}
                  rows={1}
                  style={{ height: `${Math.min(150, Math.max(24, input.split('\n').length * 24))}px` }}
                />
                <button className="btn-send" onClick={handleSend} disabled={!input.trim() || isLoading}>
                  <Send size={18} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
