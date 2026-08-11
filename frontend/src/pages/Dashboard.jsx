import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Book, Target, TrendingUp, RefreshCw, Plus, Trash2, ArrowRight, Library, FileText, User, LogOut, LayoutDashboard } from 'lucide-react';
import Sidebar from '../components/Sidebar';
import './Dashboard.css';

const EXAM_ICONS = { "NEET": "🩺", "TNPSC": "🏛️" };
const SUBJECT_ICONS = {
  "Physics": "⚛️", "Chemistry": "🧪", "Botany": "🌿", "Zoology": "🦁",
  "History": "📜", "Geography": "🌍", "Polity": "⚖️",
  "Economics": "📈", "Science": "🔬", "Current Affairs": "📰",
};

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [spaces, setSpaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ totalQuestions: 0, overallAcc: 0, bestSubject: '—' });

  const loadData = async () => {
    setLoading(true);
    try {
      const spacesData = await api.get('/spaces');
      setSpaces(spacesData || []);
            // Use the new batch stats endpoint for efficiency (replaces N+1 calls)
        let batchStats = {};
        if (spacesData && spacesData.length > 0) {
          const queryParams = spacesData.map(sp => `space_ids=${sp.id}`).join('&');
          batchStats = await api.get(`/spaces/quiz/stats/batch?${queryParams}`).catch(() => ({}));
        }

        let totalQ = 0;
        let totalC = 0;
        let bestAcc = 0;
        let bestSubj = null;

        spacesData.forEach((sp) => {
          const st = batchStats[sp.id];
          if (st && st.total_all > 0) {
            totalQ += st.total_all;
            totalC += st.correct_all;
            if (st.accuracy_all > bestAcc) {
              bestAcc = st.accuracy_all;
              bestSubj = sp.subject;
            }
          }
        });
      
      const overallAcc = totalQ > 0 ? (totalC / totalQ) * 100 : 0;
      setStats({
        totalQuestions: totalQ,
        overallAcc,
        bestSubject: bestSubj || '—'
      });
      
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDeleteSpace = async (spaceId, subjectName) => {
    if (window.confirm(`Delete ${subjectName}? This cannot be undone.`)) {
      try {
        await api.delete(`/spaces/${spaceId}`);
        loadData();
      } catch (err) {
        alert("Failed to delete space: " + err.message);
      }
    }
  };

  return (
    <div className="dashboard-layout">
      <Sidebar />

      <main className="dashboard-main animate-fade-in">
        <header className="dashboard-header">
          <div className="welcome-msg">
            <h1>👋 Welcome back, {user?.name || 'Student'}!</h1>
            <p>Ready to continue your learning journey?</p>
          </div>
          <div className="action-bar">
            <button className="btn-secondary" onClick={loadData} disabled={loading}>
              <RefreshCw size={16} className={loading ? 'animate-pulse' : ''} />
              Refresh
            </button>
          </div>
        </header>

      {/* Stats Row */}
      <div className="stats-grid">
        <div className="stat-card">
          <span className="label"><Library size={18} /> Learning Spaces</span>
          <span className="value">{spaces.length}</span>
        </div>
        <div className="stat-card">
          <span className="label"><Book size={18} /> Total Questions</span>
          <span className="value">{stats.totalQuestions}</span>
        </div>
        <div className="stat-card">
          <span className="label"><Target size={18} /> Overall Accuracy</span>
          <span className="value">{stats.overallAcc.toFixed(1)}%</span>
        </div>
        <div className="stat-card">
          <span className="label"><TrendingUp size={18} /> Best Subject</span>
          <span className="value">{stats.bestSubject}</span>
        </div>
      </div>

      {stats.totalQuestions > 0 && (
        <div className="progress-container">
          <div className="progress-bar" style={{ width: `${stats.overallAcc}%` }}></div>
        </div>
      )}

      {/* Spaces Section */}
      <section className="spaces-section">
        <div className="section-header">
          <h2>Your Learning Spaces</h2>
          <button className="btn-primary" onClick={() => navigate('/select-exam')}>
            <Plus size={18} /> Add New Space
          </button>
        </div>

        {loading ? (
          <div className="empty-state">
            <p>Loading your study spaces...</p>
          </div>
        ) : spaces.length === 0 ? (
          <div className="empty-state">
            <p>You don't have any Learning Spaces yet.</p>
            <button className="btn-primary" style={{ margin: '0 auto' }} onClick={() => navigate('/select-exam')}>
              <Plus size={18} /> Create Your First Space
            </button>
          </div>
        ) : (
          <div className="spaces-grid">
            {spaces.map(space => {
              const examIcon = EXAM_ICONS[space.exam_id] || "📖";
              const subjIcon = SUBJECT_ICONS[space.subject] || "📚";
              const date = space.created_at ? space.created_at.substring(0, 10) : "";
              
              return (
                <div key={space.id} className="space-card">
                  <div>
                    <div className="space-icon">{subjIcon}</div>
                    <div className="space-details">
                      <h3>{space.subject}</h3>
                      <p>{examIcon} {space.exam_id} • Created: {date}</p>
                    </div>
                  </div>
                  <div className="space-actions">
                    <button 
                      className="btn-open"
                      onClick={() => navigate(`/space/${space.id}`, { state: { space } })}
                    >
                      Open Space <ArrowRight size={16} />
                    </button>
                    <button 
                      className="btn-icon"
                      onClick={() => handleDeleteSpace(space.id, space.subject)}
                      title="Delete Space"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
      </main>
    </div>
  );
}
