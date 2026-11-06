import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { api } from '../services/api';
import { 
  MessageSquare, 
  Files, 
  Layers, 
  ClipboardCheck, 
  BarChart2, 
  ArrowLeft,
  BookOpen,
  Bot,
  BookMarked
} from 'lucide-react';
import './Space.css';

// Import Tabs
import SharedChatTab from '../components/Space/SharedChatTab';
import MaterialsTab from '../components/Space/MaterialsTab';
import FlashcardsTab from '../components/Space/FlashcardsTab';
import ExamLabTab from '../components/Space/ExamLabTab';
import ReportsTab from '../components/Space/ReportsTab';
import NotesTab from '../components/Space/NotesTab';

export default function Space() {
  const { spaceId, tab } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  
  const initialTab = tab ? tab.toLowerCase() : (location.state?.activeTab || 'learn');
  const [space, setSpace] = useState(location.state?.space || null);
  const [activeTab, setActiveTab] = useState(initialTab);
  const [activeFile, setActiveFile] = useState(null);
  const [loading, setLoading] = useState(!space);

  useEffect(() => {
    if (tab) {
      setActiveTab(tab.toLowerCase());
    }
  }, [tab]);

  const handleTabChange = (newTab, file = null) => {
    setActiveTab(newTab);
    if (file) setActiveFile(file);
    navigate(`/spaces/${spaceId}/${newTab}`, { replace: true, state: { space, activeTab: newTab } });
  };


  useEffect(() => {
    if (!space) {
      const fetchSpace = async () => {
        try {
          const data = await api.get(`/spaces/${spaceId}`);
          setSpace(data);
        } catch (err) {
          console.error("Failed to load space", err);
          navigate('/dashboard');
        } finally {
          setLoading(false);
        }
      };
      fetchSpace();
    }
  }, [spaceId, space, navigate]);

  if (loading) {
    return (
      <div className="space-layout" style={{ justifyContent: 'center', alignItems: 'center' }}>
        <p>Loading your space...</p>
      </div>
    );
  }

  if (!space) return null;

  const renderContent = () => {
    switch (activeTab) {
      case 'learn':
        return <SharedChatTab key="learn" spaceId={spaceId} space={space} chatType="AI_TUTOR" />;
      case 'mystudygpt':
      case 'file_chat':
        return (
          <SharedChatTab 
            key="materials_shared_chat" 
            spaceId={spaceId} 
            space={space} 
            chatType="MYSTUDYGPT" 
            initialActiveDoc={activeTab === 'file_chat' ? activeFile : null} 
          />
        );
      case 'materials':
        return <MaterialsTab spaceId={spaceId} space={space} onTabChange={handleTabChange} />;
      case 'flashcards':
        return <FlashcardsTab spaceId={spaceId} space={space} />;
      case 'examlab':
        return <ExamLabTab spaceId={spaceId} space={space} onTabChange={handleTabChange} />;
      case 'notes':
        return <NotesTab spaceId={spaceId} space={space} onTabChange={handleTabChange} />;
      case 'reports':
        return <ReportsTab spaceId={spaceId} space={space} />;

      default:
        return <SharedChatTab key="default" spaceId={spaceId} space={space} chatType="AI_TUTOR" />;
    }
  };

  return (
    <div className="space-layout animate-fade-in">
      <aside className="space-sidebar">
        <div className="space-brand" onClick={() => navigate('/dashboard')}>
          <BookOpen size={24} />
          <h2>Vinaval AI</h2>
        </div>

        <div className="space-info">
          <h3>{space.subject}</h3>
          <p>{space.exam_id} Preparation</p>
        </div>

        <nav className="nav-links">
          <button 
            className={`nav-item ${activeTab === 'learn' ? 'active' : ''}`}
            onClick={() => setActiveTab('learn')}
          >
            <MessageSquare size={18} />
            AI Tutor
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'mystudygpt' ? 'active' : ''}`}
            onClick={() => setActiveTab('mystudygpt')}
          >
            <Bot size={18} />
            My Study GPT
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'materials' ? 'active' : ''}`}
            onClick={() => setActiveTab('materials')}
          >
            <Files size={18} />
            Materials
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'flashcards' ? 'active' : ''}`}
            onClick={() => setActiveTab('flashcards')}
          >
            <Layers size={18} />
            Flashcards
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'examlab' ? 'active' : ''}`}
            onClick={() => handleTabChange('examlab')}
          >
            <ClipboardCheck size={18} />
            Exam Lab
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'notes' ? 'active' : ''}`}
            onClick={() => handleTabChange('notes')}
          >
            <BookMarked size={18} />
            Smart Notes
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'reports' ? 'active' : ''}`}
            onClick={() => handleTabChange('reports')}
          >
            <BarChart2 size={18} />
            Reports
          </button>

        </nav>

        <div className="space-footer">
          <button className="btn-dashboard" onClick={() => navigate('/dashboard')}>
            <ArrowLeft size={16} /> Back to Dashboard
          </button>
        </div>
      </aside>

      <main className="space-main">
        <div className="space-content-wrapper">
          {renderContent()}
        </div>
      </main>
    </div>
  );
}
