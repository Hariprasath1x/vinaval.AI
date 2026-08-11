import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { BarChart2, Target, CheckCircle, BrainCircuit, Activity, Info, Clock, ChevronRight } from 'lucide-react';
import ResultAnalysisPanel from './ResultAnalysisPanel';
import './ReportsTab.css';

export default function ReportsTab({ spaceId, space }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [history, setHistory] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.get(`/spaces/${spaceId}/quiz/stats`);
        setStats(data);
        const histData = await api.get(`/spaces/${spaceId}/quiz/history`);
        setHistory(histData || []);
      } catch (err) {
        console.error("Failed to load stats/history:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, [spaceId]);

  const handleViewAnalysis = async (sessionId) => {
    setLoadingAnalysis(true);
    setSelectedSessionId(sessionId);
    try {
      const data = await api.get(`/spaces/${spaceId}/quiz/sessions/${sessionId}/analysis`);
      setAnalysis(data);
    } catch (err) {
      alert("Failed to load analysis or analysis not yet generated.");
      setSelectedSessionId(null);
    } finally {
      setLoadingAnalysis(false);
    }
  };

  const handleBackToHistory = () => {
    setSelectedSessionId(null);
    setAnalysis(null);
  };

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading your analytics...</div>;
  }

  if (selectedSessionId && analysis) {
    return (
      <div className="reports-container animate-fade-in" style={{ padding: 0, backgroundColor: 'transparent', border: 'none' }}>
        <ResultAnalysisPanel analysis={analysis} spaceId={spaceId} onBack={handleBackToHistory} />
      </div>
    );
  }

  if (loadingAnalysis) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading analysis...</div>;
  }

  if (!stats || stats.total_all === 0) {
    return (
      <div className="reports-container animate-fade-in">
        <div className="reports-header">
          <h2><BarChart2 size={24} /> Performance Analytics</h2>
          <p>Track your progress and mastery over time.</p>
        </div>
        
        <div className="empty-state" style={{ padding: '4rem 2rem' }}>
          <Activity size={48} style={{ color: 'var(--text-muted)', margin: '0 auto 1rem' }} />
          <h3 style={{ marginBottom: '0.5rem' }}>No Data Yet</h3>
          <p>Take some practice quizzes or mock exams in the <strong>Exam Lab</strong> to see your analytics here.</p>
        </div>
      </div>
    );
  }

  const accPractice = stats.total_practice > 0 ? (stats.correct_practice / stats.total_practice) * 100 : 0;
  const accMock = stats.total_exam > 0 ? (stats.correct_exam / stats.total_exam) * 100 : 0;

  return (
    <div className="reports-container animate-fade-in">
      <div className="reports-header">
        <h2><BarChart2 size={24} /> Performance Analytics</h2>
        <p>Review your progress for <strong>{space?.subject}</strong>.</p>
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-icon"><Target size={24} /></div>
          <div className="metric-val">{stats.accuracy_all.toFixed(1)}%</div>
          <div className="metric-lbl">Overall Accuracy</div>
        </div>
        
        <div className="metric-card">
          <div className="metric-icon"><BrainCircuit size={24} /></div>
          <div className="metric-val">{stats.total_all}</div>
          <div className="metric-lbl">Questions Attempted</div>
        </div>
        
        <div className="metric-card">
          <div className="metric-icon"><CheckCircle size={24} /></div>
          <div className="metric-val">{stats.correct_all}</div>
          <div className="metric-lbl">Correct Answers</div>
        </div>
      </div>

      <div className="accuracy-section">
        <h3><Activity size={20} /> Accuracy Breakdown</h3>
        <div className="acc-bar-container">
          
          <div className="acc-bar-item">
            <div className="acc-label-row">
              <span>Practice Mode</span>
              <span>{stats.total_practice > 0 ? accPractice.toFixed(1) : '—'}%</span>
            </div>
            <div className="acc-progress-bg">
              <div 
                className="acc-progress-fill" 
                style={{ width: `${accPractice}%` }}
              ></div>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', alignSelf: 'flex-end' }}>
              {stats.correct_practice} / {stats.total_practice} correct
            </span>
          </div>
          
          <div className="acc-bar-item">
            <div className="acc-label-row">
              <span>Mock Exam Mode</span>
              <span>{stats.total_exam > 0 ? accMock.toFixed(1) : '—'}%</span>
            </div>
            <div className="acc-progress-bg">
              <div 
                className="acc-progress-fill mock" 
                style={{ width: `${accMock}%` }}
              ></div>
            </div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', alignSelf: 'flex-end' }}>
              {stats.correct_exam} / {stats.total_exam} correct
            </span>
          </div>

        </div>
      </div>

      <div className="info-alert">
        <Info size={24} />
        <p>
          <strong>Keep it up!</strong> 
          <br/>
          Your analytics are calculated across all your quiz sessions within this specific Learning Space. Try to aim for an overall accuracy above 85% before taking the real exam.
        </p>
      </div>
      
      {history.length > 0 && (
        <div className="test-history-section">
          <h3><Clock size={20} /> Recent Test History</h3>
          <div className="history-list">
            {history.map(session => {
              const d = new Date(session.created_at);
              const dateStr = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
              return (
                <div key={session.id} className="history-card">
                  <div className="hist-main">
                    <h4>{session.topic || 'Full Mock Exam'} {session.is_exam && <span className="badge-exam">EXAM</span>}</h4>
                    <p>Score: {session.correct_answers}/{session.total_questions} ({session.score_pct}%) • {dateStr}</p>
                  </div>
                  <div className="hist-actions">
                    {session.is_completed ? (
                      <button className="btn-secondary" onClick={() => handleViewAnalysis(session.id)}>
                        Result Analysis <ChevronRight size={16} />
                      </button>
                    ) : (
                      <span className="badge-incomplete">Incomplete</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
}
