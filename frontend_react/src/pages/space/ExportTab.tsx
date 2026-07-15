import { useState } from 'react'
import { Download, FileText, Loader2 } from 'lucide-react'
import { spaceService } from '../../services/spaceService'
import { useToast } from '../../components/Toast'

interface ExportTabProps {
  spaceId: number
  subject: string
  examId: string
}

export default function ExportTab({ spaceId, subject, examId }: ExportTabProps) {
  const [exporting, setExporting] = useState(false)
  const { success: toastSuccess, error: toastError, info: toastInfo } = useToast()

  const downloadFile = (content: string, filename: string, mime: string) => {
    const blob = new Blob([content], { type: mime })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleExportNotes = async () => {
    setExporting(true)
    try {
      const note = await spaceService.getNote(spaceId)
      if (!note.content.trim()) {
        toastInfo('Your notes are empty. Write something in the Notes tab first.')
        return
      }
      const header = `# ${examId} — ${subject} Notes\nExported on ${new Date().toLocaleDateString('en-IN', { dateStyle: 'long' })}\n\n---\n\n`
      downloadFile(header + note.content, `${examId}_${subject.replace(/\s+/g, '_')}_notes.md`, 'text/markdown')
      toastSuccess('Notes exported as Markdown!')
    } catch (e: any) {
      toastError(e?.message ?? 'Export failed')
    } finally {
      setExporting(false)
    }
  }

  const handleExportNotesTxt = async () => {
    setExporting(true)
    try {
      const note = await spaceService.getNote(spaceId)
      if (!note.content.trim()) {
        toastInfo('Your notes are empty. Write something in the Notes tab first.')
        return
      }
      const header = `${examId} — ${subject} Notes\nExported: ${new Date().toLocaleDateString()}\n${'='.repeat(40)}\n\n`
      downloadFile(header + note.content, `${examId}_${subject.replace(/\s+/g, '_')}_notes.txt`, 'text/plain')
      toastSuccess('Notes exported as plain text!')
    } catch (e: any) {
      toastError(e?.message ?? 'Export failed')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-12">
      <h2 className="text-lg font-semibold text-white mb-1">Export</h2>
      <p className="text-slate-400 text-sm mb-8">
        Download your notes from this Learning Space in different formats.
      </p>

      <div className="space-y-3">
        {/* Markdown export */}
        <div className="rounded-xl p-5 flex items-center justify-between" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg flex items-center justify-center"
                 style={{ backgroundColor: 'var(--accent-soft)', border: '1px solid rgba(90,127,245,0.2)' }}>
              <FileText className="w-4 h-4" style={{ color: 'var(--accent)' }} />
            </div>
            <div>
              <div className="text-sm font-medium text-white">Notes as Markdown</div>
              <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>.md file — works with Obsidian, Notion, etc.</div>
            </div>
          </div>
          <button
            id="export-md-btn"
            onClick={handleExportNotes}
            disabled={exporting}
            className="btn-outline text-sm py-2 px-4 flex-shrink-0"
          >
            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          </button>
        </div>

        {/* Plain text export */}
        <div className="rounded-xl p-5 flex items-center justify-between" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg border flex items-center justify-center" style={{ backgroundColor: 'var(--bg)', borderColor: 'var(--border)' }}>
              <FileText className="w-4 h-4" style={{ color: 'var(--text)' }} />
            </div>
            <div>
              <div className="text-sm font-medium text-white">Notes as Plain Text</div>
              <div className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>.txt file — universal format</div>
            </div>
          </div>
          <button
            id="export-txt-btn"
            onClick={handleExportNotesTxt}
            disabled={exporting}
            className="btn-outline text-sm py-2 px-4 flex-shrink-0"
          >
            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <div className="mt-8 p-4 rounded-xl bg-white/[0.02] border border-white/5">
        <p className="text-xs text-slate-500 leading-relaxed">
          <strong className="text-slate-400">Tip:</strong> Your notes are written in the <strong className="text-slate-400">Notes</strong> tab.
          Export as Markdown to preserve formatting, or as plain text for universal compatibility.
          PDF export is coming in a future update.
        </p>
      </div>
    </div>
  )
}
