import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Bot, User, Paperclip, X, Settings, ChevronDown, ChevronUp, Trash2 } from 'lucide-react';
import './LearnTab.css';

export default function LearnTab({ spaceId, space }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showOptions, setShowOptions] = useState(false);
  const [chatLang, setChatLang] = useState('auto');
  
  // Read active doc from sessionStorage to share between tabs if needed, or keep in React state.
  // We'll use local state for simplicity, initialized from sessionStorage if available.
  const [activeDoc, setActiveDoc] = useState(() => {
    const saved = sessionStorage.getItem(`activeDoc_${spaceId}`);
    return saved ? JSON.parse(saved) : null;
  });

  const chatEndRef = useRef(null);

  // Sync activeDoc to sessionStorage
  useEffect(() => {
    if (activeDoc) {
      sessionStorage.setItem(`activeDoc_${spaceId}`, JSON.stringify(activeDoc));
    } else {
      sessionStorage.removeItem(`activeDoc_${spaceId}`);
    }
  }, [activeDoc, spaceId]);

  // Listen for custom event from Materials tab
  useEffect(() => {
    const handleSetDoc = (e) => {
      if (e.detail && e.detail.spaceId === spaceId) {
        setActiveDoc(e.detail.doc);
      }
    };
    window.addEventListener('set-active-doc', handleSetDoc);
    return () => window.removeEventListener('set-active-doc', handleSetDoc);
  }, [spaceId]);

  // Load initial history
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const history = await api.get(`/spaces/${spaceId}/messages`);
        if (history) {
          setMessages(history.map(m => ({ role: m.role, content: m.content })));
        }
      } catch (err) {
        console.error("Failed to load chat history:", err);
      }
    };
    loadHistory();
  }, [spaceId]);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

    const payload = {
      content: userMessage,
      lang: chatLang
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
        setMessages(prev => {
          const newMessages = [...prev];
          newMessages[newMessages.length - 1].content = fullResponse;
          return newMessages;
        });
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => {
        const newMessages = [...prev];
        newMessages[newMessages.length - 1].content += `\n\n❌ Error: ${err.message}`;
        return newMessages;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="learn-tab-container animate-fade-in">
      <div className="learn-header">
        <h2><Bot size={24} /> AI Tutor</h2>
        <p>Ask anything related to {space?.subject}.</p>
      </div>

      {activeDoc ? (
        <div className="active-doc-banner animate-fade-in">
          <div className="doc-info">
            <Paperclip size={20} className="brand-icon" />
            <div className="doc-info-text">
              <strong>Knowledge Source: {activeDoc.filename}</strong>
              {activeDoc.topics?.length > 0 && (
                <span>Topics: {activeDoc.topics.slice(0,3).join(', ')}{activeDoc.topics.length > 3 ? '...' : ''}</span>
              )}
            </div>
          </div>
          <button className="btn-remove-doc" onClick={() => setActiveDoc(null)}>
            <X size={16} /> Remove
          </button>
        </div>
      ) : (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', marginBottom: '1rem' }}>
          📚 <strong>Using:</strong> Pre-loaded syllabus books only. Upload a document in the <strong>Materials</strong> tab to focus the AI on your notes.
        </p>
      )}

      <div className="options-expander">
        <div className="options-header" onClick={() => setShowOptions(!showOptions)}>
          <Settings size={16} /> Options {showOptions ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
        {showOptions && (
          <div className="options-content animate-fade-in">
            <div className="lang-select">
              <label>AI Reply Language</label>
              <select value={chatLang} onChange={(e) => setChatLang(e.target.value)}>
                <option value="auto">🤖 Auto-Detect</option>
                <option value="en">🇬🇧 English</option>
                <option value="ta">🇮🇳 Tamil</option>
              </select>
            </div>
            <button className="btn-clear" onClick={() => setMessages([])}>
              <Trash2 size={16} style={{ verticalAlign: 'middle', marginRight: '4px' }}/> 
              Clear chat display
            </button>
          </div>
        )}
      </div>

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
              {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
            </div>
            <div className="message-content">
              {msg.role === 'user' ? (
                <p style={{ margin: 0 }}>{msg.content}</p>
              ) : (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {msg.content || '...'}
                </ReactMarkdown>
              )}
            </div>
          </div>
        ))}
        <div ref={chatEndRef} />
      </div>

      <div className="chat-input-wrapper">
        <div className="chat-input-container">
          <textarea
            placeholder={activeDoc ? `Ask about '${activeDoc.filename}'...` : "Ask your AI tutor..."}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={1}
            style={{ 
              height: `${Math.min(150, Math.max(24, input.split('\n').length * 24))}px`
            }}
          />
          <button 
            className="btn-send" 
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
          >
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
