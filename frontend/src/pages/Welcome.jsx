import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Welcome.css';

const COPY_DATA = {
  en: {
    q: "What is photosynthesis?",
    a: "Photosynthesis is the process by which green plants convert light energy into chemical energy, making glucose from carbon dioxide and water in the chloroplasts.",
    source: "Biology · Photosynthesis in Higher Plants",
    isTamil: false,
  },
  ta: {
    q: "ஒளிச்சேர்க்கை என்றால் என்ன?",
    a: "ஒளிச்சேர்க்கை என்பது பச்சைத் தாவரங்கள் ஒளி ஆற்றலை வேதி ஆற்றலாக மாற்றும் செயல்முறை. பசுங்கணிகத்தில் கார்பன் டை ஆக்சைடும் நீரும் சேர்ந்து குளுக்கோஸ் உருவாகிறது.",
    source: "Biology · Photosynthesis in Higher Plants",
    isTamil: true,
  },
};

export default function Welcome() {
  const { user } = useAuth();

  const [currentLang, setCurrentLang] = useState('en');
  const [displayedText, setDisplayedText] = useState('');
  const [isFading, setIsFading] = useState(false);

  const typingTimerRef = useRef(null);
  const autoSwitchTimerRef = useRef(null);
  const fadeTimeoutRef = useRef(null);

  const startTyping = (fullText) => {
    if (typingTimerRef.current) clearInterval(typingTimerRef.current);
    setDisplayedText('');
    let i = 0;
    typingTimerRef.current = setInterval(() => {
      i++;
      setDisplayedText(fullText.slice(0, i));
      if (i >= fullText.length) {
        clearInterval(typingTimerRef.current);
      }
    }, 22);
  };

  const handleLanguageChange = (lang, isManualClick = false) => {
    if (isManualClick && autoSwitchTimerRef.current) {
      clearInterval(autoSwitchTimerRef.current);
    }
    if (lang === currentLang && !isFading) return;

    setIsFading(true);
    if (fadeTimeoutRef.current) clearTimeout(fadeTimeoutRef.current);

    fadeTimeoutRef.current = setTimeout(() => {
      setCurrentLang(lang);
      setIsFading(false);
      startTyping(COPY_DATA[lang].a);
    }, 250);
  };

  useEffect(() => {
    // Start initial typing in English
    startTyping(COPY_DATA.en.a);

    // Auto toggle between English and Tamil every 9 seconds
    autoSwitchTimerRef.current = setInterval(() => {
      setCurrentLang((prev) => {
        const nextLang = prev === 'en' ? 'ta' : 'en';
        setIsFading(true);
        if (fadeTimeoutRef.current) clearTimeout(fadeTimeoutRef.current);

        fadeTimeoutRef.current = setTimeout(() => {
          setIsFading(false);
          startTyping(COPY_DATA[nextLang].a);
        }, 250);

        return nextLang;
      });
    }, 9000);

    return () => {
      if (typingTimerRef.current) clearInterval(typingTimerRef.current);
      if (autoSwitchTimerRef.current) clearInterval(autoSwitchTimerRef.current);
      if (fadeTimeoutRef.current) clearTimeout(fadeTimeoutRef.current);
    };
  }, []);

  const currentContent = COPY_DATA[currentLang];

  return (
    <div className="welcome-page">
      {/* ---------- LEFT COLUMN ---------- */}
      <section className="welcome-left">
        <nav className="welcome-nav">
          <Link to="/" className="welcome-brand">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
              <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
            </svg>
            Vinaval AI
          </Link>

          <div className="welcome-nav-actions">
            {user ? (
              <Link className="welcome-nav-link" to="/dashboard">
                Dashboard
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M13 6l6 6-6 6" />
                </svg>
              </Link>
            ) : (
              <Link className="welcome-nav-link" to="/login?tab=login">
                Log in
              </Link>
            )}
          </div>
        </nav>

        <div className="welcome-hero">
          <div className="welcome-pill">
            <span className="welcome-dot"></span>
            NEET &middot; TNPSC &middot; English + தமிழ்
          </div>

          <h1>
            Ask. Learn.<br />
            <em>Crack it.</em>
          </h1>

          <p className="welcome-sub">
            Your AI learning arena for competitive exams. Get answers grounded in your study material, practise on demand, and learn in the language you think in.
          </p>

          <div className="welcome-cta">
            {user ? (
              <>
                <Link className="welcome-btn welcome-btn-primary" to="/dashboard">
                  Go to Dashboard
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </Link>
                <Link className="welcome-btn welcome-btn-ghost" to="/mock-tests">
                  Practice Tests
                </Link>
              </>
            ) : (
              <>
                <Link className="welcome-btn welcome-btn-primary" to="/signup">
                  Get Started
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </Link>
                <Link className="welcome-btn welcome-btn-ghost" to="/login?tab=login">
                  I have an account
                </Link>
              </>
            )}
          </div>
        </div>

        <div className="welcome-stats">
          <div className="welcome-stat">
            <b>2</b>
            <span>Languages</span>
          </div>
          <div className="welcome-stat">
            <b>NEET + TNPSC</b>
            <span>Exam tracks</span>
          </div>
          <div className="welcome-stat">
            <b>Cited</b>
            <span>Source-backed answers</span>
          </div>
        </div>
      </section>

      {/* ---------- RIGHT COLUMN ---------- */}
      <section className="welcome-right">
        <div className="welcome-panel">
          <div className="welcome-grid-dots" aria-hidden="true" />
          <div className="welcome-orb a" aria-hidden="true" />
          <div className="welcome-orb b" aria-hidden="true" />

          {/* Book watermark */}
          <svg className="welcome-big-book" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
          </svg>

          {/* Floating Card 1: Biology Progress */}
          <div className="welcome-float-card welcome-fc1">
            <svg className="welcome-ring" viewBox="0 0 48 48" aria-hidden="true">
              <circle className="welcome-ring-bg" cx="24" cy="24" r="20" />
              <circle className="welcome-ring-fg" cx="24" cy="24" r="20" />
            </svg>
            <div>
              <b>Biology</b>
              <span>78% mastered</span>
            </div>
          </div>

          {/* Chat Demonstration Card */}
          <div className="welcome-chat">
            <div className="welcome-chat-head">
              <div className="welcome-chat-title">
                <i /> Vinaval Tutor
              </div>
              <div className="welcome-toggle" role="tablist" aria-label="Language selection">
                <button
                  type="button"
                  className={currentLang === 'en' ? 'on' : ''}
                  onClick={() => handleLanguageChange('en', true)}
                  aria-selected={currentLang === 'en'}
                >
                  EN
                </button>
                <button
                  type="button"
                  className={currentLang === 'ta' ? 'on' : ''}
                  onClick={() => handleLanguageChange('ta', true)}
                  aria-selected={currentLang === 'ta'}
                >
                  தமிழ்
                </button>
              </div>
            </div>

            <div className={`welcome-msg welcome-user ${currentContent.isTamil ? 'welcome-ta' : ''} ${isFading ? 'welcome-fade' : ''}`}>
              {currentContent.q}
            </div>

            <div className={`welcome-msg welcome-ai ${currentContent.isTamil ? 'welcome-ta' : ''} ${isFading ? 'welcome-fade' : ''}`}>
              <span>{displayedText}</span>
              <span className="welcome-caret" aria-hidden="true" />
              <div>
                <span className="welcome-src">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                  </svg>
                  {currentContent.source}
                </span>
              </div>
            </div>
          </div>

          {/* Floating Card 2: Mock Test Ready */}
          <div className="welcome-float-card welcome-fc2">
            <div className="welcome-ico" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 11l3 3L22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
            </div>
            <div>
              <b>Mock test ready</b>
              <span>TNPSC Group 4 &middot; 50 Qs</span>
            </div>
          </div>

          {/* Floating Card 3: Streak */}
          <div className="welcome-float-card welcome-fc3">
            <div>
              <b>12-day streak</b>
              <span>Keep it going</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
