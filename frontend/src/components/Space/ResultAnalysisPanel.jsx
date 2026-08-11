import React from 'react';
import { Target, CheckCircle2, AlertTriangle, ArrowRight, Lightbulb, UserCheck, RefreshCw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import './ResultAnalysisPanel.css';
import { api } from '../../services/api';

export default function ResultAnalysisPanel({ analysis, spaceId, onBack }) {
  if (!analysis) return null;

  const {
    score_pct, performance_level, overall_summary, ai_narrative, ai_generated,
    correct_count, incorrect_count, skipped_count,
    strong_areas, developing_areas, priority_areas, mistake_patterns, recommendations
  } = analysis;

  const getPerformanceLabel = (level) => {
    switch (level) {
      case 'excellent': return 'Excellent Performance';
      case 'good': return 'Good Performance';
      case 'developing': return 'Developing Performance';
      case 'needs_work': return 'Needs Work';
      default: return 'Performance Overview';
    }
  };
  
  const handleRetryAi = async () => {
    try {
      // For now, retry just re-triggers complete_session if needed, 
      // but typically we'd have a specific endpoint. 
      // We will skip retry implementation for now as it needs a backend route.
      alert("AI Regeneration requires a dedicated retry endpoint, not yet implemented.");
    } catch(err) {
      console.error(err);
    }
  };

  return (
    <div className="result-analysis-panel animate-fade-in">
      <div className="analysis-header">
        <button className="btn-secondary back-btn" onClick={onBack}>
          <ArrowRight style={{ transform: 'rotate(180deg)' }} size={16} /> Back
        </button>
        <h2>Your Performance Analysis</h2>
      </div>

      <div className="perf-banner">
        <div className="score-ring">
          <svg viewBox="0 0 36 36" className="circular-chart">
            <path className="circle-bg"
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <path className="circle"
              strokeDasharray={`${score_pct}, 100`}
              d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            />
            <text x="18" y="20.35" className="percentage">{Math.round(score_pct)}%</text>
          </svg>
        </div>
        <div className="perf-summary">
          <h3>{getPerformanceLabel(performance_level)}</h3>
          <p className="stats-row">
            <span className="stat-pill correct"><CheckCircle2 size={14}/> {correct_count} correct</span>
            <span className="stat-pill incorrect"><AlertTriangle size={14}/> {incorrect_count} incorrect</span>
            <span className="stat-pill skipped"><ArrowRight size={14}/> {skipped_count} skipped</span>
          </p>
        </div>
      </div>

      {(ai_narrative || overall_summary) && (
        <div className="mentor-card stagger-1">
          <h3><UserCheck size={20} /> Academic Mentor Summary</h3>
          {overall_summary && <p className="overall-summary">{overall_summary}</p>}
          {ai_narrative && (
            <div className="ai-narrative-content">
              <ReactMarkdown>{ai_narrative}</ReactMarkdown>
            </div>
          )}
          {!ai_generated && (
            <div className="ai-failed-msg">
              <p>AI generation was unavailable. Showing calculated metrics only.</p>
              <button className="btn-secondary" onClick={handleRetryAi}><RefreshCw size={14}/> Retry AI Narrative</button>
            </div>
          )}
        </div>
      )}

      <div className="areas-grid stagger-2">
        <div className="area-card strong-areas">
          <h4><CheckCircle2 size={18} /> Strong Areas</h4>
          {strong_areas && strong_areas.length > 0 ? (
            <ul>
              {strong_areas.map((area, i) => (
                <li key={i}>
                  <span className="topic-name">{area.name}</span>
                  <span className="topic-acc">{Math.round(area.accuracy)}%</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">No strong areas identified yet.</p>
          )}
        </div>

        <div className="area-card developing-areas">
          <h4><Target size={18} /> Developing Areas</h4>
          {developing_areas && developing_areas.length > 0 ? (
            <ul>
              {developing_areas.map((area, i) => (
                <li key={i}>
                  <span className="topic-name">{area.name}</span>
                  <span className="topic-acc">{Math.round(area.accuracy)}%</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty-state">No developing areas identified.</p>
          )}
        </div>
      </div>

      {priority_areas && priority_areas.length > 0 && (
        <div className="priority-card stagger-3">
          <h4><AlertTriangle size={20} /> Priority Areas for Improvement</h4>
          <div className="priority-list">
            {priority_areas.map((area, idx) => (
              <div key={idx} className="priority-item">
                <span className="p-num">0{idx + 1}</span>
                <div className="p-details">
                  <h5>{area.name}</h5>
                  <p>Accuracy: {Math.round(area.accuracy)}%</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {mistake_patterns && mistake_patterns.length > 0 && (
        <div className="mistakes-card stagger-4">
          <h4><Lightbulb size={20} /> What Your Mistakes Tell You</h4>
          <div className="patterns-grid">
            {mistake_patterns.map((pattern, idx) => (
              <div key={idx} className="pattern-item">
                <h5>{pattern.type.replace('_', ' ').toUpperCase()}</h5>
                <p>{pattern.description}</p>
                {pattern.affected_topics && pattern.affected_topics.length > 0 && (
                  <p className="affected"><strong>Affected:</strong> {pattern.affected_topics.join(', ')}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {recommendations && recommendations.length > 0 && (
        <div className="recommendations-card stagger-5">
          <h4><Target size={20} /> What You Should Do Next</h4>
          <ul className="recs-list">
            {recommendations.map((rec, idx) => (
              <li key={idx} className={`rec-item priority-${rec.priority.toLowerCase()}`}>
                <div className="rec-action">{rec.action}</div>
                <div className="rec-body">
                  <strong>{rec.topic}</strong>
                  <p>{rec.detail}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

    </div>
  );
}
