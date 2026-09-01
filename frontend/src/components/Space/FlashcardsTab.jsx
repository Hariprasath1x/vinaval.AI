import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../../services/api';
import { getTopics } from '../../utils/constants';
import { Layers, Sparkles, RefreshCw, X, Check, FolderOpen, Trash2, PartyPopper } from 'lucide-react';
import './FlashcardsTab.css';

export default function FlashcardsTab({ spaceId, space }) {
  const [topicChoice, setTopicChoice] = useState('');
  const [customTopic, setCustomTopic] = useState('');
  const [count, setCount] = useState(8);
  const [lang, setLang] = useState('en');
  const [generating, setGenerating] = useState(false);

  const [queue, setQueue] = useState([]);
  const [mastered, setMastered] = useState(0);
  const [total, setTotal] = useState(0);
  const [activeTopic, setActiveTopic] = useState('');
  const [showBack, setShowBack] = useState(false);

  const [savedTopics, setSavedTopics] = useState([]);
  const [loadingTopics, setLoadingTopics] = useState(true);

  const availTopics = useMemo(() => space ? getTopics(space.subject) : [], [space]);
  
  useEffect(() => {
    if (availTopics.length > 0) {
      setTopicChoice(availTopics[0]);
    }
  }, [availTopics]);

  const loadSavedTopics = useCallback(async () => {
    try {
      const topics = await api.get(`/spaces/${spaceId}/flashcards/topics`);
      setSavedTopics(topics || []);
    } catch (err) {
      console.error("Failed to load topics:", err);
    } finally {
      setLoadingTopics(false);
    }
  }, [spaceId]);

  useEffect(() => {
    loadSavedTopics();
  }, [loadSavedTopics]);

  const handleGenerate = async (e) => {
    e.preventDefault();
    const finalTopic = topicChoice.startsWith('✏️') ? customTopic.trim() : topicChoice;
    
    if (!finalTopic) {
      alert("Please select or enter a topic.");
      return;
    }

    setGenerating(true);
    setQueue([]);
    setMastered(0);
    setTotal(0);
    setActiveTopic(finalTopic);
    setShowBack(false);

    try {
      const stream = api.streamObjects(`/spaces/${spaceId}/flashcards/generate`, {
        topic: finalTopic,
        count: parseInt(count),
        lang
      });

      for await (const msg of stream) {
        if (msg.event === "deck") {
          // Deck initialized
        } else if (msg.event === "flashcard") {
          setQueue(prev => [...prev, msg.data]);
          setTotal(prev => prev + 1);
        } else if (msg.event === "complete") {
          loadSavedTopics();
        } else if (msg.event === "error") {
          alert("Generation error: " + (msg.data.detail || JSON.stringify(msg.data)));
        }
      }
    } catch (err) {
      alert("Generation failed: " + err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleLoad = async (topic) => {
    try {
      const cards = await api.get(`/spaces/${spaceId}/flashcards`, { topic });
      if (cards && cards.length > 0) {
        setQueue(cards);
        setMastered(0);
        setTotal(cards.length);
        setActiveTopic(topic);
        setShowBack(false);
      }
    } catch (err) {
      alert("Failed to load flashcards: " + err.message);
    }
  };

  const handleDeleteTopic = async (topic) => {
    if (!window.confirm(`Delete all flashcards for '${topic}'?`)) return;
    try {
      await api.delete(`/spaces/${spaceId}/flashcards/${encodeURIComponent(topic)}`);
      loadSavedTopics();
      if (activeTopic === topic) {
        resetSession();
      }
    } catch (err) {
      alert("Delete failed: " + err.message);
    }
  };

  const resetSession = () => {
    setQueue([]);
    setMastered(0);
    setTotal(0);
    setActiveTopic('');
    setShowBack(false);
  };

  const handleHard = () => {
    if (queue.length === 0) return;
    const newQueue = [...queue];
    const card = newQueue.shift();
    newQueue.push(card); // Move to back
    setQueue(newQueue);
    setShowBack(false);
  };

  const handleEasy = () => {
    if (queue.length === 0) return;
    const newQueue = [...queue];
    newQueue.shift(); // Remove from queue
    setQueue(newQueue);
    setMastered(prev => prev + 1);
    setShowBack(false);
  };

  return (
    <div className="flashcards-container animate-fade-in">
      <div className="flashcards-header">
        <h2><Layers size={24} /> Flashcards</h2>
        <p>Generate AI-powered flashcards. Rate each card — Hard cards repeat until you master them!</p>
      </div>

      {!queue.length && mastered === 0 && (
        <div className="generate-card">
          <form onSubmit={handleGenerate}>
            <div className="generate-form">
              <div className="form-group">
                <label>Chapter / Topic</label>
                {availTopics.length > 0 ? (
                  <select value={topicChoice} onChange={e => setTopicChoice(e.target.value)}>
                    {availTopics.map(t => <option key={t} value={t}>{t}</option>)}
                    <option value="✏️ Custom (type below)">✏️ Custom (type below)</option>
                  </select>
                ) : (
                  <input 
                    type="text" 
                    value={topicChoice} 
                    onChange={e => setTopicChoice(e.target.value)} 
                    placeholder="e.g. Photosynthesis"
                    required
                  />
                )}
                
                {topicChoice.startsWith('✏️') && (
                  <input 
                    type="text" 
                    value={customTopic} 
                    onChange={e => setCustomTopic(e.target.value)}
                    placeholder="Type your custom topic..." 
                    required 
                    style={{ marginTop: '0.5rem' }}
                  />
                )}
              </div>
              
              <div className="form-group">
                <label># Cards</label>
                <input 
                  type="number" 
                  min="2" max="20" 
                  value={count} 
                  onChange={e => setCount(e.target.value)} 
                  required 
                />
              </div>

              <div className="form-group">
                <label>Language</label>
                <select value={lang} onChange={e => setLang(e.target.value)}>
                  <option value="en">English</option>
                  <option value="ta">Tamil (தமிழ்)</option>
                </select>
              </div>
            </div>

            <button type="submit" className="btn-primary" disabled={generating}>
              {generating ? 'Generating...' : <><Sparkles size={16} /> Generate Flashcards</>}
            </button>
          </form>
        </div>
      )}

      {queue.length > 0 && (
        <div className="session-container animate-fade-in">
          <div className="session-stats">
            <span><strong>Topic:</strong> {activeTopic}</span>
            <span>✅ Mastered: {mastered}/{total} &nbsp;&nbsp; 🔁 Remaining: {queue.length}</span>
          </div>
          
          <div className="progress-container">
            <div className="progress-bar" style={{ width: `${(mastered / total) * 100}%` }}></div>
          </div>

          <div className="flashcard-active">
            <h3>{showBack ? '💡 Back' : '📋 Front'}</h3>
            <div className="flashcard-text">
              {showBack ? queue[0].back : queue[0].front}
            </div>
            {!showBack && <div className="flashcard-hint">Think of the answer, then flip!</div>}
          </div>

          <div className="card-actions">
            {!showBack ? (
              <button className="btn-flip" onClick={() => setShowBack(true)}>
                <RefreshCw size={18} /> Flip Card
              </button>
            ) : (
              <>
                <button className="btn-hard" onClick={handleHard}>
                  <X size={18} /> Hard — Again
                </button>
                <button className="btn-easy" onClick={handleEasy}>
                  <Check size={18} /> Got it!
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {queue.length === 0 && mastered > 0 && total > 0 && (
        <div className="session-complete animate-fade-in">
          <h3><PartyPopper size={32} style={{ verticalAlign: 'middle', marginRight: '10px' }} /> Congratulations!</h3>
          <p style={{ marginBottom: '2rem' }}>You mastered all <strong>{total}</strong> cards in this session!</p>
          <button className="btn-primary" style={{ margin: '0 auto' }} onClick={resetSession}>
            <RefreshCw size={16} /> Start a New Session
          </button>
        </div>
      )}

      {/* Saved Topics: only show when there is no active session */}
      {queue.length === 0 && (
        <div className="saved-topics-section" style={{ marginTop: '2rem' }}>
          <h3 style={{ marginBottom: '1rem', fontSize: '1.2rem' }}>Saved Flashcard Topics</h3>
          {loadingTopics ? (
            <p>Loading...</p>
          ) : savedTopics.length === 0 ? (
            <div className="empty-state" style={{ padding: '2rem' }}>
              <Layers size={40} style={{ color: 'var(--text-muted)', margin: '0 auto 1rem' }} />
              <p>No saved flashcard sets yet. Generate one above!</p>
            </div>
          ) : (
            <div className="saved-topics-list">
              {savedTopics.map(t => (
                <div key={t} className="saved-topic-card">
                  <h4>{t}</h4>
                  <div className="topic-actions">
                    <button className="btn-load" onClick={() => handleLoad(t)}>
                      <FolderOpen size={16} /> Load
                    </button>
                    <button className="btn-icon" onClick={() => handleDeleteTopic(t)}>
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
