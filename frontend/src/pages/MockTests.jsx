import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import Sidebar from '../components/Sidebar';
import { FileText, Plus, Search, Calendar, Target, CheckCircle } from 'lucide-react';
import './MockTests.css';

export default function MockTests() {
  const navigate = useNavigate();
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [spaces, setSpaces] = useState([]);
  const [showSpaceSelect, setShowSpaceSelect] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const [histData, spacesData] = await Promise.all([
          api.get('/spaces/quiz/global-history').catch(() => []),
          api.get('/spaces').catch(() => [])
        ]);
        setHistory(histData || []);
        setSpaces(spacesData || []);
      } catch (err) {
        console.error("Failed to load mock tests:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleStartMockTest = (spaceId) => {
    const space = spaces.find(s => s.id === spaceId);
    if (space) {
      navigate(`/space/${spaceId}`, { state: { space, activeTab: 'examlab' } });
    }
  };

  return (
    <div className="mocktests-container">
      <Sidebar />
      <main className="mocktests-main animate-fade-in">
        <header className="mocktests-header">
          <div>
            <h1>Mock Tests</h1>
            <p>Track your performance across all mock exams.</p>
          </div>
          <button className="btn-primary" onClick={() => setShowSpaceSelect(true)}>
            <Plus size={18} /> New Mock Test
          </button>
        </header>

        {showSpaceSelect && (
          <div className="space-selector animate-fade-in">
            <div className="space-selector-content">
              <h3>Select a Subject</h3>
              <p>Choose a learning space to generate a mock test from:</p>
              <div className="spaces-list">
                {spaces.length === 0 ? (
                  <p>No learning spaces available. Please create one first.</p>
                ) : (
                  spaces.map(space => (
                    <button 
                      key={space.id} 
                      className="space-btn"
                      onClick={() => handleStartMockTest(space.id)}
                    >
                      {space.subject} ({space.exam_id})
                    </button>
                  ))
                )}
              </div>
              <button className="btn-secondary mt-2" onClick={() => setShowSpaceSelect(false)}>
                Cancel
              </button>
            </div>
          </div>
        )}

        <div className="mocktests-content">
          {loading ? (
            <div className="loading-state">Loading history...</div>
          ) : history.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon"><FileText size={48} /></div>
              <h2>No Mock Tests Yet</h2>
              <p>You haven't taken any mock tests across your learning spaces.</p>
              <button className="btn-primary" onClick={() => setShowSpaceSelect(true)}>
                Start Your First Mock Test
              </button>
            </div>
          ) : (
            <div className="history-grid">
              {history.map(session => (
                <div key={session.id} className="mocktest-card">
                  <div className="card-header">
                    <span className="badge">{session.is_exam ? "Mock Exam" : "Practice"}</span>
                    <span className="date"><Calendar size={14}/> {new Date(session.created_at).toLocaleDateString()}</span>
                  </div>
                  <h3 className="topic-title">{session.topic || 'General Assessment'}</h3>
                  
                  <div className="stats-row">
                    <div className="stat">
                      <Target size={16} />
                      <span>{session.total_questions} Questions</span>
                    </div>
                    <div className="stat text-success">
                      <CheckCircle size={16} />
                      <span>{session.correct_answers} Correct</span>
                    </div>
                  </div>
                  
                  <div className="accuracy-bar-container">
                    <div className="accuracy-header">
                      <span>Accuracy</span>
                      <span>{session.total_questions > 0 ? Math.round((session.correct_answers / session.total_questions) * 100) : 0}%</span>
                    </div>
                    <div className="accuracy-bar-bg">
                      <div 
                        className="accuracy-bar-fill" 
                        style={{ width: `${session.total_questions > 0 ? (session.correct_answers / session.total_questions) * 100 : 0}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
