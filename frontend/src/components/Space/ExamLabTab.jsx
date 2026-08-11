import React, { useState, useEffect, useRef } from 'react';
import { api } from '../../services/api';
import { getTopics } from '../../utils/constants';
import { ClipboardCheck, Target, Clock, Lightbulb, CheckCircle2, XCircle, Bot, RefreshCw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import ResultAnalysisPanel from './ResultAnalysisPanel';
import './ExamLabTab.css';

const MOCK_EXAM_DURATION_SECONDS = 15 * 60; // 15 mins

export default function ExamLabTab({ spaceId, space }) {
  const [isExamMode, setIsExamMode] = useState(false);
  const [topicChoice, setTopicChoice] = useState('');
  const [customTopic, setCustomTopic] = useState('');
  const [count, setCount] = useState(5);
  const [lang, setLang] = useState('en');
  const [generating, setGenerating] = useState(false);

  const [questions, setQuestions] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [quizTopic, setQuizTopic] = useState('');
  
  // Timer State
  const [timeRemaining, setTimeRemaining] = useState(0);
  const timerRef = useRef(null);

  // Results State
  const [results, setResults] = useState({});
  const [aiReview, setAiReview] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [showAnalysis, setShowAnalysis] = useState(false);

  const availTopics = React.useMemo(() => space ? getTopics(space.subject) : [], [space]);
  
  useEffect(() => {
    if (availTopics.length > 0) {
      setTopicChoice(availTopics[0]);
    }
  }, [availTopics]);

  useEffect(() => {
    if (isExamMode) {
      setCount(15);
    } else {
      setCount(5);
    }
  }, [isExamMode]);

  const submitQuiz = React.useCallback(async (currentAnswers = answers, force = false) => {
    if (!force && Object.keys(currentAnswers).length < questions.length) {
      alert("⚠️ Please answer all questions before submitting.");
      return;
    }

    setSubmitting(true);
    if (timerRef.current) clearInterval(timerRef.current);

    try {
      const reviewResults = [];
      const detailedResults = {};

      for (const q of questions) {
        const ans = currentAnswers[q.id] || null; // null if time up and unanswered
        const res = await api.post(`/spaces/${spaceId}/quiz/attempt`, {
          question_id: q.id,
          user_answer: ans,
          is_exam: isExamMode,
          session_id: sessionId
        });
        if (res) {
          detailedResults[q.id] = res;
          reviewResults.push({ topic: q.topic, is_correct: res.is_correct });
        }
      }
      
      setResults(detailedResults);
      setAnswers(currentAnswers); // Sync answers if forced

      // ── Step 2: Complete session & Generate Performance Analysis ──
      setAnalyzing(true);
      try {
        const compData = await api.post(`/spaces/${spaceId}/quiz/sessions/${sessionId}/complete`);
        if (compData && compData.analysis) {
           setAnalysis(compData.analysis);
        }
      } catch (err) {
        console.error("Failed to complete session analysis:", err);
      } finally {
        setAnalyzing(false);
      }
      
      setSubmitted(true);
    } catch (err) {
      alert("Failed to submit quiz: " + err.message);
    } finally {
      setSubmitting(false);
    }
  }, [answers, questions, isExamMode, sessionId, spaceId]);

  const handleTimeUp = React.useCallback(async () => {
    alert("⏰ Time's up! Submitting your answers automatically.");
    await submitQuiz(answers, true); // force submit with whatever we have
  }, [answers, submitQuiz]);

  // Timer Effect
  useEffect(() => {
    if (questions.length > 0 && isExamMode && !submitted && timeRemaining > 0) {
      timerRef.current = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            clearInterval(timerRef.current);
            handleTimeUp();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [questions, isExamMode, submitted, timeRemaining, handleTimeUp]);

  const handleGenerate = async (e) => {
    e.preventDefault();
    const targetTopic = isExamMode ? "Full Mock Exam" : (topicChoice.startsWith('✏️') ? customTopic.trim() : topicChoice);
    
    if (!isExamMode && !targetTopic) {
      alert("Please select or enter a topic.");
      return;
    }

    setGenerating(true);
    try {
      const data = await api.post(`/spaces/${spaceId}/quiz/generate`, {
        topic: isExamMode ? null : targetTopic,
        count: parseInt(count),
        lang
      });

      if (data && data.questions) {
        setQuestions(data.questions);
        setSessionId(data.session_id);
        setAnswers({});
        setSubmitted(false);
        setShowAnalysis(false);
        setAnalysis(null);
        setQuizTopic(targetTopic);
        
        if (isExamMode) {
          setTimeRemaining(MOCK_EXAM_DURATION_SECONDS);
        }
      }
    } catch (err) {
      alert("Generation failed: " + err.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleReset = () => {
    setQuestions([]);
    setAnswers({});
    setSubmitted(false);
    setResults({});
    setAiReview('');
    setAnalysis(null);
    setShowAnalysis(false);
    setTimeRemaining(0);
  };

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="examlab-container animate-fade-in">
      <div className="examlab-header">
        <h2><ClipboardCheck size={24} /> Exam Lab</h2>
        <p>Generate practice questions or take a full mock exam.</p>
      </div>

      {!questions.length && (
        <div className="setup-card">
          <h3>Generate Quiz</h3>
          
          <div className="mode-toggle">
            <button 
              className={`mode-btn ${!isExamMode ? 'active' : ''}`}
              onClick={() => setIsExamMode(false)}
            >
              Practice (by Topic)
            </button>
            <button 
              className={`mode-btn ${isExamMode ? 'active' : ''}`}
              onClick={() => setIsExamMode(true)}
            >
              Full Mock Exam
            </button>
          </div>

          <form onSubmit={handleGenerate} className="generate-form">
            <div className="form-group">
              <label>Chapter / Topic</label>
              {isExamMode ? (
                <input type="text" value="Whole Syllabus" disabled />
              ) : availTopics.length > 0 ? (
                <select value={topicChoice} onChange={e => setTopicChoice(e.target.value)}>
                  {availTopics.map(t => <option key={t} value={t}>{t}</option>)}
                  <option value="✏️ Custom (type below)">✏️ Custom (type below)</option>
                </select>
              ) : (
                <input 
                  type="text" 
                  value={topicChoice} 
                  onChange={e => setTopicChoice(e.target.value)} 
                  placeholder="e.g. Cell Division"
                  required
                />
              )}
              
              {!isExamMode && topicChoice.startsWith('✏️') && (
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
              <label># Questions</label>
              <input 
                type="number" 
                min="1" max="30" 
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

            <button type="submit" className="btn-primary" style={{ gridColumn: '1 / -1' }} disabled={generating}>
              {generating ? 'Generating...' : <><Target size={16} /> Generate {isExamMode ? 'Mock Exam' : 'Practice Quiz'}</>}
            </button>
          </form>
        </div>
      )}

      {/* Active Quiz */}
      {questions.length > 0 && !submitted && (
        <div className="quiz-section animate-fade-in">
          {isExamMode && (
            <div className={`timer-banner ${timeRemaining < 120 ? 'danger' : timeRemaining < 300 ? 'warning' : ''}`}>
              <div className="timer-header">
                <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}><Clock size={18} /> Time Remaining</span>
                <span>{formatTime(timeRemaining)}</span>
              </div>
              <div className="progress-container" style={{ margin: 0, height: '4px' }}>
                <div className="progress-bar" style={{ width: `${(timeRemaining / MOCK_EXAM_DURATION_SECONDS) * 100}%` }}></div>
              </div>
            </div>
          )}

          <div className="quiz-header">
            <h3>{quizTopic}</h3>
            <span>{Object.keys(answers).length} / {questions.length} answered</span>
          </div>

          {questions.map((q, idx) => (
            <div key={q.id} className="question-card">
              <div className="question-text">Q{idx + 1}. {q.question}</div>
              <div className="options-list">
                {['a', 'b', 'c', 'd'].map(opt => (
                  <label key={opt} className={`option-item ${answers[q.id] === opt ? 'selected' : ''}`}>
                    <input 
                      type="radio" 
                      name={`q_${q.id}`} 
                      value={opt}
                      checked={answers[q.id] === opt}
                      onChange={() => setAnswers(prev => ({ ...prev, [q.id]: opt }))}
                    />
                    <div className="option-label">
                      <strong>{opt.toUpperCase()}.</strong> {q[`option_${opt}`]}
                    </div>
                  </label>
                ))}
              </div>
            </div>
          ))}

          <button 
            className="btn-primary" 
            style={{ padding: '1rem', fontSize: '1.1rem', justifyContent: 'center' }} 
            onClick={() => submitQuiz()}
            disabled={submitting || analyzing}
          >
            {submitting ? 'Submitting Answers...' : analyzing ? 'Analyzing Performance...' : '📩 Submit Quiz'}
          </button>
        </div>
      )}

      {/* Results */}
      {submitted && showAnalysis && analysis && (
        <ResultAnalysisPanel analysis={analysis} spaceId={spaceId} onBack={() => setShowAnalysis(false)} />
      )}

      {submitted && !showAnalysis && (
        <div className="results-summary animate-fade-in">
          {(() => {
            const correctCount = Object.values(results).filter(r => r.is_correct).length;
            const pct = (correctCount / questions.length) * 100;
            return (
              <div className="score-banner">
                <h3>🎉 Quiz Completed!</h3>
                <div className="score-stats">
                  <div className="score-stat">
                    <span className="val">{correctCount} / {questions.length}</span>
                    <span className="lbl">Score</span>
                  </div>
                  <div className="score-stat">
                    <span className="val">{pct.toFixed(0)}%</span>
                    <span className="lbl">Accuracy</span>
                  </div>
                  <div className="score-stat">
                    <span className="val">{isExamMode ? '🎓 Exam' : '🏋️ Practice'}</span>
                    <span className="lbl">Mode</span>
                  </div>
                </div>
                {analysis && (
                  <button className="btn-primary" style={{marginTop: '1rem'}} onClick={() => setShowAnalysis(true)}>
                    <Target size={18} /> View Result Analysis
                  </button>
                )}
              </div>
            );
          })()}

          {aiReview && (
            <div className="ai-review">
              <h4><Bot size={20} /> AI Tutor Review</h4>
              <div className="ai-review-content">
                <ReactMarkdown>{aiReview}</ReactMarkdown>
              </div>
            </div>
          )}

          <div className="detailed-results">
            <h3>Detailed Results</h3>
            {questions.map((q, idx) => {
              const res = results[q.id] || {};
              const userAns = answers[q.id];
              const isCorrect = res.is_correct;
              const correctOpt = res.correct_option;

              return (
                <div key={q.id} className={`result-card ${isCorrect ? 'correct' : 'incorrect'}`}>
                  <div className="result-header">
                    {isCorrect ? <CheckCircle2 size={20} color="var(--success)" /> : <XCircle size={20} color="var(--error)" />}
                    <span>Q{idx + 1}. {q.question}</span>
                  </div>

                  <div className="result-options">
                    {['a', 'b', 'c', 'd'].map(opt => {
                      const text = q[`option_${opt}`];
                      let className = "opt-res ";
                      let icon = "　"; // spacer
                      
                      if (opt === correctOpt) {
                        className += "is-correct";
                        icon = "✅ ";
                      } else if (opt === userAns && !isCorrect) {
                        className += "is-wrong";
                        icon = "❌ ";
                      }

                      return (
                        <div key={opt} className={className}>
                          <span>{icon}</span>
                          <div><strong>{opt.toUpperCase()}.</strong> {text}</div>
                        </div>
                      );
                    })}
                  </div>

                  {res.explanation && (
                    <div className="explanation-box">
                      <p><Lightbulb size={16} style={{ display: 'inline', verticalAlign: 'text-bottom', marginRight: '4px' }} /> <strong>Explanation:</strong> {res.explanation}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <button className="btn-secondary" style={{ alignSelf: 'center', padding: '0.75rem 1.5rem' }} onClick={handleReset}>
            <RefreshCw size={18} /> Generate a New Quiz
          </button>
        </div>
      )}
    </div>
  );
}
