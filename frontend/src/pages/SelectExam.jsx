import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { ArrowLeft, Rocket } from 'lucide-react';
import './SelectExam.css';

const EXAMS = {
  "NEET": {
    label: "Medical Entrance",
    description: "National Eligibility cum Entrance Test for undergraduate medical admissions.",
    icon: "🩺",
    subjects: [
      { name: "Physics", icon: "⚛️" },
      { name: "Chemistry", icon: "🧪" },
      { name: "Botany", icon: "🌿" },
      { name: "Zoology", icon: "🦁" },
    ],
  },
  "TNPSC": {
    label: "Tamil Nadu Civil Services",
    description: "Tamil Nadu Public Service Commission exam for government service recruitment.",
    icon: "🏛️",
    subjects: [
      { name: "History", icon: "📜" },
      { name: "Geography", icon: "🌍" },
      { name: "Polity", icon: "⚖️" },
      { name: "Economics", icon: "📈" },
      { name: "Science", icon: "🔬" },
      { name: "Current Affairs", icon: "📰" },
    ],
  },
};

export default function SelectExam() {
  const navigate = useNavigate();
  const [selectedExam, setSelectedExam] = useState('NEET');
  const [selectedSubject, setSelectedSubject] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCreateSpace = async () => {
    if (!selectedExam || !selectedSubject) return;
    
    setLoading(true);
    try {
      const space = await api.post('/spaces', {
        exam_id: selectedExam,
        subject: selectedSubject
      });
      
      if (space && space.id) {
        navigate(`/space/${space.id}`, { state: { space } });
      }
    } catch (err) {
      alert("Failed to create space: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const currentExamInfo = EXAMS[selectedExam];

  return (
    <div className="select-exam-container animate-fade-in">
      <div className="page-header">
        <h1>🎯 Choose Your Exam & Subject</h1>
        <p>Select an exam and then a subject to open (or create) your personalized Learning Space.</p>
      </div>

      <div className="exam-selection">
        {Object.entries(EXAMS).map(([examId, info]) => (
          <div 
            key={examId} 
            className={`exam-card ${selectedExam === examId ? 'active' : ''}`}
            onClick={() => {
              setSelectedExam(examId);
              setSelectedSubject(null);
            }}
          >
            <div className="exam-card-header">
              <span className="exam-card-icon">{info.icon}</span>
              <div className="exam-card-title">
                <h2>{examId}</h2>
                <span>{info.label}</span>
              </div>
            </div>
            <p className="exam-description">{info.description}</p>
          </div>
        ))}
      </div>

      {currentExamInfo && (
        <div className="subject-selection animate-fade-in">
          <h3>{currentExamInfo.icon} {selectedExam} — Select a Subject</h3>
          <div className="subjects-grid">
            {currentExamInfo.subjects.map(subj => (
              <button 
                key={subj.name}
                className={`subject-btn ${selectedSubject === subj.name ? 'active' : ''}`}
                onClick={() => setSelectedSubject(subj.name)}
              >
                <span className="icon">{subj.icon}</span>
                <span>{subj.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="action-footer">
        <button className="btn-large btn-secondary" onClick={() => navigate('/dashboard')}>
          <ArrowLeft size={18} /> Back to Dashboard
        </button>
        {selectedSubject && (
          <button 
            className="btn-large btn-large-primary animate-fade-in" 
            onClick={handleCreateSpace}
            disabled={loading}
          >
            {loading ? (
              'Setting up...'
            ) : (
              <>
                <Rocket size={18} /> Open Learning Space
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
