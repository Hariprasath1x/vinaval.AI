import React, { useState, useEffect } from 'react';
import { api } from '../../services/api';
import { Files, UploadCloud, FileText, CheckCircle, Trash2, MessageSquare, BookOpen } from 'lucide-react';
import './MaterialsTab.css';

export default function MaterialsTab({ spaceId, onTabChange }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState(null);
  const [uploadResult, setUploadResult] = useState(null);

  const loadDocuments = async () => {
    try {
      const data = await api.get(`/spaces/${spaceId}/documents`);
      setDocuments(data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [spaceId]);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const result = await api.post(`/spaces/${spaceId}/documents`, formData, false);
      if (result) {
        setUploadResult(result);
        setFile(null);
        loadDocuments();
      }
    } catch (err) {
      alert("Upload failed: " + err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm("Delete this document?")) return;
    try {
      await api.delete(`/spaces/${spaceId}/documents/${docId}`);
      
      // Clear active doc from session storage if it was deleted
      const saved = sessionStorage.getItem(`activeDoc_${spaceId}`);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.id === docId) {
          sessionStorage.removeItem(`activeDoc_${spaceId}`);
        }
      }

      loadDocuments();
    } catch (err) {
      alert("Delete failed: " + err.message);
    }
  };

  const handleChatWithFile = (doc) => {
    const activeDoc = {
      id: doc.id,
      filename: doc.filename,
      chunk_count: doc.chunk_count,
      topics: doc.topics || []
    };
    
    // Dispatch event for LearnTab
    const event = new CustomEvent('set-active-doc', { 
      detail: { spaceId, doc: activeDoc } 
    });
    window.dispatchEvent(event);
    
    // Switch to Learn tab
    if (onTabChange) {
      onTabChange('learn');
    }
  };

  return (
    <div className="materials-container animate-fade-in">
      <div className="materials-header">
        <h2><Files size={24} /> Your Study Materials</h2>
        <p>Upload question banks, notes, or previous papers. The AI will index them for chat and quizzes.</p>
      </div>

      <div className="upload-card">
        <h3>Upload a Document</h3>
        <form className="upload-form" onSubmit={handleUpload}>
          <div className="file-input-wrapper">
            <input 
              type="file" 
              accept=".pdf,.txt" 
              onChange={(e) => setFile(e.target.files[0])} 
              disabled={uploading}
            />
            <div className="file-input-content">
              <UploadCloud size={32} />
              {file ? (
                <span><strong>{file.name}</strong> selected</span>
              ) : (
                <span>Click or drag a PDF/TXT file here</span>
              )}
            </div>
          </div>
          
          <button 
            type="submit" 
            className="btn-primary" 
            disabled={!file || uploading}
            style={{ alignSelf: 'flex-start' }}
          >
            {uploading ? 'Uploading & Indexing...' : '📤 Upload & Index'}
          </button>
        </form>

        {uploadResult && (
          <div className="upload-result animate-fade-in">
            <h4><CheckCircle size={18} /> {uploadResult.filename} uploaded successfully!</h4>
            
            <div className="result-stats">
              <div className="stat-item">
                <span className="val">{uploadResult.chunk_count || '?'}</span>
                <span className="lbl">Chunks</span>
              </div>
              <div className="stat-item">
                <span className="val">{uploadResult.pages || '?'}</span>
                <span className="lbl">Pages</span>
              </div>
              <div className="stat-item">
                <span className="val">{uploadResult.topics?.length || 0}</span>
                <span className="lbl">Topics</span>
              </div>
            </div>

            {uploadResult.topics?.length > 0 && (
              <div className="result-topics">
                <p>Detected Topics:</p>
                <div className="topic-pills">
                  {uploadResult.topics.slice(0, 6).map((t, i) => (
                    <span key={i} className="topic-pill">{t}</span>
                  ))}
                  {uploadResult.topics.length > 6 && (
                    <span className="topic-pill">+{uploadResult.topics.length - 6} more</span>
                  )}
                </div>
              </div>
            )}

            <button 
              className="btn-primary btn-chat-with-file" 
              onClick={() => handleChatWithFile(uploadResult)}
            >
              <MessageSquare size={16} /> Chat with this file →
            </button>
          </div>
        )}
      </div>

      <div className="documents-list-section">
        <h3>Indexed Documents</h3>
        
        {loading ? (
          <p>Loading documents...</p>
        ) : documents.length === 0 ? (
          <div className="empty-state" style={{ padding: '2rem' }}>
            <FileText size={40} style={{ color: 'var(--text-muted)', margin: '0 auto 1rem' }} />
            <p>No documents uploaded yet. Upload your first document above!</p>
          </div>
        ) : (
          <div className="documents-list">
            {documents.map(doc => (
              <div key={doc.id} className="doc-card">
                <div className="doc-info">
                  <div className="doc-name">
                    {doc.file_type === 'pdf' ? <FileText size={16} /> : <Files size={16}/>}
                    {doc.filename}
                  </div>
                  <div className="doc-meta">
                    {doc.source === 'book' ? (
                      <><BookOpen size={12} style={{ display: 'inline', marginRight: '4px' }}/> Syllabus Book</>
                    ) : (
                      <>{doc.chunk_count ? `${doc.chunk_count} chunks` : doc.file_type.toUpperCase()}</>
                    )}
                    {doc.topics?.length > 0 && ` • ${doc.topics.slice(0,3).join(', ')}${doc.topics.length > 3 ? '...' : ''}`}
                  </div>
                </div>
                
                <div className="doc-actions">
                  <button 
                    className="btn-icon" 
                    title="Chat with this file"
                    onClick={() => handleChatWithFile(doc)}
                  >
                    <MessageSquare size={16} />
                  </button>
                  {doc.source !== 'book' && (
                    <button 
                      className="btn-icon" 
                      title="Delete document"
                      onClick={() => handleDelete(doc.id)}
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
