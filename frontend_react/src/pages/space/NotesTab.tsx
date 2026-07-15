import { useState, useEffect, useRef, useCallback } from 'react'
import { Save, Check, Loader2, FileText } from 'lucide-react'
import { spaceService } from '../../services/spaceService'
import { useToast } from '../../components/Toast'

interface NotesTabProps {
  spaceId: number
  subject: string
}

type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

const AUTOSAVE_DELAY_MS = 1500

export default function NotesTab({ spaceId, subject }: NotesTabProps) {
  const [content, setContent] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const lastSavedRef = useRef<string>('')

  // Load note on mount
  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    spaceService.getNote(spaceId)
      .then((note) => {
        if (!cancelled) {
          setContent(note.content ?? '')
          lastSavedRef.current = note.content ?? ''
        }
      })
      .catch(() => {
        if (!cancelled) setContent('')
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => { cancelled = true }
  }, [spaceId])

  const { success: toastSuccess, error: toastError } = useToast()

  // Debounced auto-save
  const save = useCallback(async (text: string, showFeedback = false) => {
    if (text === lastSavedRef.current) return
    setSaveStatus('saving')
    try {
      await spaceService.saveNote(spaceId, { content: text })
      lastSavedRef.current = text
      setSaveStatus('saved')
      if (showFeedback) toastSuccess('Notes saved!')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch {
      setSaveStatus('error')
      if (showFeedback) toastError('Failed to save notes')
    }
  }, [spaceId, toastSuccess, toastError])

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value
    setContent(text)
    setSaveStatus('idle')

    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => save(text), AUTOSAVE_DELAY_MS)
  }

  // Manual save on Ctrl+S
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        if (debounceRef.current) clearTimeout(debounceRef.current)
        save(content)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [content, save])

  // Cleanup debounce on unmount — save immediately
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
      if (content !== lastSavedRef.current) {
        spaceService.saveNote(spaceId, { content }).catch(() => {})
      }
    }
  }, [content, spaceId])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--accent)' }} />
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full" style={{ minHeight: '0' }}>

      {/* ── Toolbar ── */}
      <div className="flex-shrink-0 flex items-center justify-between px-4 py-3 border-b border-white/5">
        <div className="flex items-center gap-2 text-slate-400 text-sm">
          <FileText className="w-4 h-4" />
          <span>{subject} Notes</span>
          {content.length > 0 && (
            <span className="text-slate-600 text-xs">
              · {content.split(/\s+/).filter(Boolean).length} words
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {saveStatus === 'saving' && (
            <div className="flex items-center gap-1.5 text-xs text-slate-500">
              <Loader2 className="w-3 h-3 animate-spin" />
              <span>Saving…</span>
            </div>
          )}
          {saveStatus === 'saved' && (
            <div className="flex items-center gap-1.5 text-xs text-emerald-400">
              <Check className="w-3 h-3" />
              <span>Saved</span>
            </div>
          )}
          {saveStatus === 'error' && (
            <span className="text-xs text-red-400">Save failed</span>
          )}

          <button
            id="save-note-btn"
            onClick={() => {
              if (debounceRef.current) clearTimeout(debounceRef.current)
              save(content, true)
            }}
            disabled={saveStatus === 'saving'}
            className="btn-outline px-3 py-1.5 text-xs disabled:opacity-50"
            title="Save (Ctrl+S)"
          >
            {saveStatus === 'saving'
              ? <Loader2 className="w-3 h-3 animate-spin" />
              : <Save className="w-3 h-3" />}
            {saveStatus === 'saving' ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>

      {/* ── Editor ── */}
      <div className="flex-1 overflow-hidden">
        {content === '' && (
          <div className="pointer-events-none absolute left-0 right-0 px-8 pt-8">
            <div className="text-slate-600 text-sm leading-relaxed max-w-2xl mx-auto">
              <p className="font-medium text-slate-500 mb-2">Start taking notes…</p>
              <p>Write key concepts, formulas, mnemonics, or anything you want to remember. Notes auto-save as you type.</p>
              <p className="mt-4 text-xs text-slate-600">Tip: Use <strong className="text-slate-500">Ctrl+S</strong> to save immediately.</p>
            </div>
          </div>
        )}
        <textarea
          id="notes-textarea"
          value={content}
          onChange={handleChange}
          className="w-full h-full bg-transparent text-slate-200 text-sm leading-relaxed
                     px-6 py-6 resize-none outline-none font-mono
                     placeholder-slate-600"
          placeholder={`Write your ${subject} notes here…\n\nTip: Use plain text, markdown, or bullet points. Auto-saves every ${AUTOSAVE_DELAY_MS / 1000} seconds.`}
          spellCheck={false}
        />
      </div>
    </div>
  )
}
