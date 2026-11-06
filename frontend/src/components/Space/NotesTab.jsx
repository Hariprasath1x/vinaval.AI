import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { api } from '../../services/api';
import { getTopics } from '../../utils/constants';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { 
  BookMarked, 
  Sparkles, 
  Download, 
  Trash2, 
  Edit3, 
  Eye, 
  Search, 
  FileText, 
  CheckCircle, 
  AlertCircle, 
  UploadCloud, 
  Clock, 
  Save, 
  BookOpen
} from 'lucide-react';
import './NotesTab.css';

export default function NotesTab({ spaceId, space, onTabChange }) {
  // Navigation subtab: 'generate' or 'library'
  const [activeSubtab, setActiveSubtab] = useState('generate');

  // Generation form state
  const [sourceType, setSourceType] = useState('curriculum'); // 'curriculum' | 'document'
  const [topicChoice, setTopicChoice] = useState('');
  const [customTopic, setCustomTopic] = useState('');
  const [selectedDocId, setSelectedDocId] = useState('');
  const [docSubtopic, setDocSubtopic] = useState('');
  const [lang, setLang] = useState('en'); // 'en' | 'ta'
  const [generating, setGenerating] = useState(false);

  // Documents uploaded in this space
  const [documents, setDocuments] = useState([]);
  const [loadingDocs, setLoadingDocs] = useState(false);

  // Active Draft / Editor state
  const [draftNote, setDraftNote] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  // Saved Notes Library state
  const [savedNotes, setSavedNotes] = useState([]);
  const [loadingLibrary, setLoadingLibrary] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingId, setDeletingId] = useState(null);

  // Notification / Alert banner state
  const [alertInfo, setAlertInfo] = useState(null);

  const showAlert = (message, type = 'error') => {
    setAlertInfo({ message, type });
    if (type === 'success') {
      setTimeout(() => setAlertInfo(null), 4000);
    }
  };

  const availTopics = useMemo(() => space ? getTopics(space.subject) : [], [space]);

  useEffect(() => {
    if (availTopics.length > 0 && !topicChoice) {
      setTopicChoice(availTopics[0]);
    }
  }, [availTopics, topicChoice]);

  // Load uploaded documents for this space
  const loadDocuments = useCallback(async () => {
    setLoadingDocs(true);
    try {
      const docs = await api.get(`/spaces/${spaceId}/documents`);
      setDocuments(docs || []);
      if (docs && docs.length > 0 && !selectedDocId) {
        setSelectedDocId(docs[0].id);
      }
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setLoadingDocs(false);
    }
  }, [spaceId, selectedDocId]);

  // Load saved notes for this space
  const loadSavedNotes = useCallback(async (query = '') => {
    setLoadingLibrary(true);
    try {
      const notes = await api.listSmartNotes(spaceId, query);
      setSavedNotes(notes || []);
    } catch (err) {
      console.error("Failed to load saved notes:", err);
    } finally {
      setLoadingLibrary(false);
    }
  }, [spaceId]);

  useEffect(() => {
    loadDocuments();
    loadSavedNotes();
  }, [loadDocuments, loadSavedNotes]);

  // Handle Note Generation
  const handleGenerate = async (e) => {
    e.preventDefault();
    setAlertInfo(null);

    let finalTopic = null;
    let finalDocId = null;

    if (sourceType === 'curriculum') {
      if (topicChoice.startsWith('✏️') || !topicChoice) {
        finalTopic = customTopic.trim();
      } else {
        finalTopic = topicChoice.trim();
      }
      if (!finalTopic) {
        showAlert("Please select or enter a topic before generating.", "warning");
        return;
      }
    } else {
      if (!selectedDocId) {
        showAlert("Please select an uploaded document as the knowledge source.", "warning");
        return;
      }
      finalDocId = parseInt(selectedDocId);
      finalTopic = docSubtopic.trim() || null;
    }

    setGenerating(true);
    try {
      const payload = {
        topic: finalTopic,
        doc_id: finalDocId,
        lang,
        source_type: sourceType,
      };

      const result = await api.generateSmartNotes(spaceId, payload);
      if (result) {
        setDraftNote({
          id: null,
          title: result.title || `${finalTopic || space?.subject || 'Study'} - Smart Notes`,
          topic: result.topic || finalTopic || space?.subject || '',
          content: result.content || '',
          source_type: result.source_type || sourceType,
          lang: result.lang || lang,
          chunks_used: result.chunks_used || 0,
        });
        setIsEditing(false);
        showAlert("Smart Notes generated successfully!", "success");
      }
    } catch (err) {
      console.error("Note generation failed:", err);
      if (err.status === 429) {
        showAlert("Generation rate limit exceeded (5/min). Please wait a moment before trying again.", "warning");
      } else if (err.status === 502) {
        showAlert("AI generation service is temporarily unavailable. Please retry in a few moments.", "error");
      } else if (err.status === 401) {
        showAlert("Your session has expired. Please log in again.", "error");
        setTimeout(() => { window.location.href = '/login'; }, 1500);
      } else if (err.status === 422) {
        showAlert(`Validation error: ${err.message}`, "error");
      } else {
        showAlert(`Generation failed: ${err.message}`, "error");
      }
    } finally {
      setGenerating(false);
    }
  };

  // Save or Update note in DB
  const handleSaveNote = async () => {
    if (!draftNote || !draftNote.content.trim()) {
      showAlert("Cannot save an empty note.", "warning");
      return;
    }

    setSaving(true);
    setAlertInfo(null);
    try {
      if (draftNote.id) {
        // Update existing note
        const updated = await api.updateSmartNote(spaceId, draftNote.id, {
          title: draftNote.title.trim() || "Untitled Note",
          topic: draftNote.topic ? draftNote.topic.trim() : null,
          content: draftNote.content,
        });
        setDraftNote(updated);
        showAlert("Note updated successfully in your library!", "success");
      } else {
        // Create new note
        const created = await api.createSmartNote(spaceId, {
          title: draftNote.title.trim() || "Untitled Note",
          topic: draftNote.topic ? draftNote.topic.trim() : null,
          content: draftNote.content,
          source_type: draftNote.source_type || 'manual',
        });
        setDraftNote(created);
        showAlert("Note saved to your library!", "success");
      }
      loadSavedNotes(searchQuery);
    } catch (err) {
      console.error("Failed to save note:", err);
      showAlert(`Save failed: ${err.message}`, "error");
    } finally {
      setSaving(false);
    }
  };

  // Download note as Markdown (.md)
  const handleDownloadMarkdown = (noteToDownload = draftNote) => {
    if (!noteToDownload || !noteToDownload.content) return;
    const titleSlug = (noteToDownload.title || 'smart_notes')
      .replace(/[^a-zA-Z0-9_\u0B80-\u0BFF-]/g, '_')
      .toLowerCase();
    const blob = new Blob([noteToDownload.content], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${titleSlug}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Open note from library into view/editor
  const handleOpenFromLibrary = (note) => {
    setDraftNote(note);
    setIsEditing(false);
    setActiveSubtab('generate');
    setAlertInfo(null);
  };

  // Delete note from library
  const handleDeleteFromLibrary = async (noteId) => {
    try {
      await api.deleteSmartNote(spaceId, noteId);
      if (draftNote && draftNote.id === noteId) {
        setDraftNote(null);
      }
      setDeletingId(null);
      showAlert("Note deleted successfully.", "success");
      loadSavedNotes(searchQuery);
    } catch (err) {
      showAlert(`Failed to delete note: ${err.message}`, "error");
    }
  };

  // Search handler
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadSavedNotes(searchQuery);
  };

  return (
    <div className="notes-container animate-fade-in">
      {/* Header */}
      <div className="notes-header">
        <div className="notes-title-group">
          <h2>
            <BookMarked className="text-academic-green" size={26} />
            Smart Notes
          </h2>
          <p>
            Comprehensive, exam-oriented revision notes grounded in {space?.subject} ({space?.exam_id}) curriculum or your uploaded files.
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div className="notes-subtabs">
          <button 
            className={`subtab-btn ${activeSubtab === 'generate' ? 'active' : ''}`}
            onClick={() => setActiveSubtab('generate')}
          >
            <Sparkles size={16} />
            <span>Generate & Edit</span>
          </button>
          <button 
            className={`subtab-btn ${activeSubtab === 'library' ? 'active' : ''}`}
            onClick={() => {
              setActiveSubtab('library');
              loadSavedNotes(searchQuery);
            }}
          >
            <BookOpen size={16} />
            <span>Saved Library ({savedNotes.length})</span>
          </button>
        </div>
      </div>

      {/* Alert Banner */}
      {alertInfo && (
        <div className={`notes-alert ${alertInfo.type} animate-fade-in`}>
          {alertInfo.type === 'success' && <CheckCircle size={18} />}
          {alertInfo.type === 'error' && <AlertCircle size={18} />}
          {alertInfo.type === 'warning' && <AlertCircle size={18} />}
          <span>{alertInfo.message}</span>
          <button className="alert-close" onClick={() => setAlertInfo(null)}>×</button>
        </div>
      )}

      {/* SUBTAB 1: GENERATE & EDIT */}
      {activeSubtab === 'generate' && (
        <div className="notes-content-grid">
          {/* Configuration Form */}
          <div className="notes-card generate-card">
            <h3 className="section-title">
              <Sparkles size={18} className="text-academic-green" />
              1. Configure Knowledge Source
            </h3>

            <form onSubmit={handleGenerate} className="notes-gen-form">
              {/* Source Type Selector */}
              <div className="form-group">
                <label className="form-label">Grounding Source</label>
                <div className="source-toggle">
                  <button
                    type="button"
                    className={`source-btn ${sourceType === 'curriculum' ? 'active' : ''}`}
                    onClick={() => setSourceType('curriculum')}
                  >
                    <BookOpen size={16} />
                    <span>Syllabus Curriculum</span>
                  </button>
                  <button
                    type="button"
                    className={`source-btn ${sourceType === 'document' ? 'active' : ''}`}
                    onClick={() => setSourceType('document')}
                  >
                    <FileText size={16} />
                    <span>Uploaded Document</span>
                  </button>
                </div>
              </div>

              {/* Curriculum Mode: Topic Selector */}
              {sourceType === 'curriculum' && (
                <div className="form-group">
                  <label className="form-label">Syllabus Topic</label>
                  {availTopics.length > 0 ? (
                    <>
                      <select 
                        value={topicChoice} 
                        onChange={(e) => setTopicChoice(e.target.value)}
                        className="form-select"
                      >
                        {availTopics.map((top) => (
                          <option key={top} value={top}>{top}</option>
                        ))}
                        <option value="✏️ Custom">✏️ Custom Topic (Type below)</option>
                      </select>
                      {topicChoice.startsWith('✏️') && (
                        <input
                          type="text"
                          value={customTopic}
                          onChange={(e) => setCustomTopic(e.target.value)}
                          placeholder="e.g. Wave Optics, Thermodynamics, Photosynthesis..."
                          className="form-input mt-2"
                        />
                      )}
                    </>
                  ) : (
                    <input
                      type="text"
                      value={customTopic}
                      onChange={(e) => setCustomTopic(e.target.value)}
                      placeholder={`Enter topic name for ${space?.subject}...`}
                      className="form-input"
                    />
                  )}
                </div>
              )}

              {/* Document Mode: Document Dropdown */}
              {sourceType === 'document' && (
                <div className="form-group">
                  <label className="form-label">Select Uploaded Material</label>
                  {loadingDocs ? (
                    <p className="text-muted text-sm">Loading uploaded materials...</p>
                  ) : documents.length === 0 ? (
                    <div className="empty-docs-warning">
                      <p className="text-sm text-secondary">
                        No materials uploaded in this space yet.
                      </p>
                      {onTabChange && (
                        <button
                          type="button"
                          className="btn-link mt-1"
                          onClick={() => onTabChange('materials')}
                        >
                          <UploadCloud size={14} /> Go to Materials tab to upload PDF
                        </button>
                      )}
                    </div>
                  ) : (
                    <>
                      <select
                        value={selectedDocId}
                        onChange={(e) => setSelectedDocId(e.target.value)}
                        className="form-select"
                      >
                        {documents.map((doc) => (
                          <option key={doc.id} value={doc.id}>
                            {doc.filename} ({doc.chunk_count || 1} chunks)
                          </option>
                        ))}
                      </select>
                      <input
                        type="text"
                        value={docSubtopic}
                        onChange={(e) => setDocSubtopic(e.target.value)}
                        placeholder="Optional: Focus on specific subtopic..."
                        className="form-input mt-2"
                      />
                    </>
                  )}
                </div>
              )}

              {/* Language Selector */}
              <div className="form-group">
                <label className="form-label">Language</label>
                <select 
                  value={lang} 
                  onChange={(e) => setLang(e.target.value)}
                  className="form-select"
                >
                  <option value="en">English</option>
                  <option value="ta">Tamil (தமிழ் with English transliterations)</option>
                </select>
              </div>

              {/* Submit Button */}
              <button 
                type="submit" 
                className="btn-primary btn-generate" 
                disabled={generating || (sourceType === 'document' && documents.length === 0)}
              >
                {generating ? (
                  <>
                    <span className="spinner-sm"></span>
                    <span>Synthesizing Notes...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={18} />
                    <span>Generate Smart Notes</span>
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Active Note Preview & Editor Area */}
          <div className="notes-card preview-card">
            {draftNote ? (
              <div className="draft-view animate-fade-in">
                {/* Meta Header / Badges */}
                <div className="draft-header">
                  <div className="draft-meta-tags">
                    <span className="badge badge-lang">
                      {draftNote.lang === 'ta' ? 'தமிழ் (Tamil)' : 'English'}
                    </span>
                    <span className="badge badge-source">
                      Source: {draftNote.source_type || 'Curriculum'}
                    </span>
                    {draftNote.chunks_used > 0 && (
                      <span className="badge badge-grounding">
                        {draftNote.chunks_used} chunks grounded
                      </span>
                    )}
                    {draftNote.id && (
                      <span className="badge badge-saved">
                        Saved in Library (ID #{draftNote.id})
                      </span>
                    )}
                  </div>

                  {/* Mode Toggle & Actions */}
                  <div className="draft-actions-top">
                    <div className="mode-toggle">
                      <button
                        className={`toggle-btn ${!isEditing ? 'active' : ''}`}
                        onClick={() => setIsEditing(false)}
                        title="Reader View"
                      >
                        <Eye size={15} />
                        <span>Reader</span>
                      </button>
                      <button
                        className={`toggle-btn ${isEditing ? 'active' : ''}`}
                        onClick={() => setIsEditing(true)}
                        title="Edit Markdown"
                      >
                        <Edit3 size={15} />
                        <span>Editor</span>
                      </button>
                    </div>

                    <button 
                      className="btn-icon" 
                      onClick={() => handleDownloadMarkdown(draftNote)}
                      title="Download as Markdown"
                    >
                      <Download size={16} />
                    </button>
                    <button 
                      className="btn-icon text-danger" 
                      onClick={() => setDraftNote(null)}
                      title="Clear / Close"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>

                {/* Title & Topic Inputs */}
                <div className="draft-fields-row">
                  <div className="draft-field">
                    <label>Title</label>
                    <input
                      type="text"
                      value={draftNote.title}
                      onChange={(e) => setDraftNote({ ...draftNote, title: e.target.value })}
                      placeholder="Note Title"
                      className="form-input font-bold"
                    />
                  </div>
                  <div className="draft-field topic-field">
                    <label>Topic Tag</label>
                    <input
                      type="text"
                      value={draftNote.topic || ''}
                      onChange={(e) => setDraftNote({ ...draftNote, topic: e.target.value })}
                      placeholder="Topic tag"
                      className="form-input"
                    />
                  </div>
                </div>

                {/* Content Editor or Reader Preview */}
                <div className="draft-body">
                  {isEditing ? (
                    <textarea
                      value={draftNote.content}
                      onChange={(e) => setDraftNote({ ...draftNote, content: e.target.value })}
                      className="notes-textarea"
                      placeholder="Write or edit your Markdown notes here..."
                    />
                  ) : (
                    <div className="markdown-reader-container">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm, remarkMath]}
                        rehypePlugins={[rehypeKatex]}
                      >
                        {draftNote.content}
                      </ReactMarkdown>
                    </div>
                  )}
                </div>

                {/* Bottom Bar: Save & Actions */}
                <div className="draft-bottom-bar">
                  <button 
                    className="btn-primary btn-save" 
                    onClick={handleSaveNote}
                    disabled={saving}
                  >
                    <Save size={16} />
                    <span>{saving ? "Saving..." : (draftNote.id ? "Update Note" : "Save to Library")}</span>
                  </button>

                  <button 
                    className="btn-secondary" 
                    onClick={() => handleDownloadMarkdown(draftNote)}
                  >
                    <Download size={16} />
                    <span>Download (.md)</span>
                  </button>
                </div>
              </div>
            ) : (
              <div className="empty-preview-state">
                <BookMarked size={48} className="empty-icon text-muted" />
                <h4>No Note Active</h4>
                <p>
                  Configure your knowledge source on the left and click <strong>Generate Smart Notes</strong>, or pick a saved note from the <strong>Saved Library</strong>.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* SUBTAB 2: SAVED NOTES LIBRARY */}
      {activeSubtab === 'library' && (
        <div className="library-view animate-fade-in">
          {/* Search Header */}
          <div className="library-toolbar">
            <form onSubmit={handleSearchSubmit} className="search-box">
              <Search size={18} className="search-icon" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search saved notes by title, topic, or keyword..."
                className="search-input"
              />
              {searchQuery && (
                <button
                  type="button"
                  className="search-clear"
                  onClick={() => {
                    setSearchQuery('');
                    loadSavedNotes('');
                  }}
                >
                  ×
                </button>
              )}
            </form>
          </div>

          {/* Notes Grid / List */}
          {loadingLibrary ? (
            <div className="library-loading">
              <div className="spinner-md"></div>
              <p>Loading your saved notes...</p>
            </div>
          ) : savedNotes.length === 0 ? (
            <div className="library-empty">
              <BookOpen size={48} className="empty-icon text-muted" />
              <h4>{searchQuery ? "No matching notes found" : "No saved notes yet"}</h4>
              <p>
                {searchQuery 
                  ? `No notes match '${searchQuery}'. Try another search query or clear the filter.` 
                  : "Generate and save revision notes from your syllabus or uploaded PDFs to build your personal library."}
              </p>
              {!searchQuery && (
                <button 
                  className="btn-primary mt-3"
                  onClick={() => setActiveSubtab('generate')}
                >
                  <Sparkles size={16} /> Generate Your First Note
                </button>
              )}
            </div>
          ) : (
            <div className="library-grid">
              {savedNotes.map((note) => (
                <div key={note.id} className="note-card animate-fade-in">
                  <div className="note-card-header">
                    <div className="note-card-badges">
                      <span className="badge badge-topic">
                        {note.topic || space?.subject || 'General'}
                      </span>
                      <span className="badge badge-source">
                        {note.source_type || 'Manual'}
                      </span>
                    </div>
                    <span className="note-card-date">
                      <Clock size={12} />
                      {note.created_at ? note.created_at.substring(0, 10) : 'Recent'}
                    </span>
                  </div>

                  <h4 className="note-card-title">{note.title || 'Untitled Note'}</h4>
                  
                  <p className="note-card-excerpt">
                    {note.content.substring(0, 160).replace(/[#*`_]/g, '')}...
                  </p>

                  <div className="note-card-footer">
                    <button 
                      className="btn-open-note"
                      onClick={() => handleOpenFromLibrary(note)}
                    >
                      <Eye size={15} />
                      <span>Open Note</span>
                    </button>

                    <div className="note-card-quick-actions">
                      <button 
                        className="btn-icon-sm"
                        onClick={() => handleDownloadMarkdown(note)}
                        title="Download Markdown (.md)"
                      >
                        <Download size={14} />
                      </button>
                      
                      {deletingId === note.id ? (
                        <div className="inline-confirm">
                          <button
                            className="btn-confirm-yes"
                            onClick={() => handleDeleteFromLibrary(note.id)}
                            title="Confirm delete"
                          >
                            Yes
                          </button>
                          <button
                            className="btn-confirm-no"
                            onClick={() => setDeletingId(null)}
                            title="Cancel"
                          >
                            No
                          </button>
                        </div>
                      ) : (
                        <button 
                          className="btn-icon-sm text-danger"
                          onClick={() => setDeletingId(note.id)}
                          title="Delete note"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
