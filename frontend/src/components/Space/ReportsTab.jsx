import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { BarChart2, Target, CheckCircle, BrainCircuit, Activity, Info } from 'lucide-react';
import './ReportsTab.css';

export default function ReportsTab({ spaceId, space }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.get(`/spaces/${spaceId}/quiz/stats`);
        setStats(data);
      } catch (err) {
        console.error("Failed to load stats:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, [spaceId]);

  if (loading) {
    return <div style={{ padding: '2rem', textAlign: 'center' }}>Loading your analytics...</div>;
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

    </div>
  );
}
