import { useState, useEffect, useRef } from 'react'
import { FileText, Upload, Trash2, Loader2, BookOpen } from 'lucide-react'
import { documentService, SpaceDocument } from '../../services/documentService'
import { useToast } from '../../components/Toast'

interface MaterialsTabProps {
  spaceId: number
  subject: string
}

export default function MaterialsTab({ spaceId, subject }: MaterialsTabProps) {
  const [documents, setDocuments] = useState<SpaceDocument[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { success, error: toastError } = useToast()

  const fetchDocuments = async () => {
    try {
      const docs = await documentService.listDocuments(spaceId)
      setDocuments(docs)
    } catch (e: any) {
      toastError(e?.message ?? 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDocuments()
  }, [spaceId])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Clear input
    if (fileInputRef.current) fileInputRef.current.value = ''

    if (file.size > 10 * 1024 * 1024) {
      toastError('File size must be less than 10MB')
      return
    }

    if (!file.name.endsWith('.pdf') && !file.name.endsWith('.txt')) {
      toastError('Only PDF and TXT files are supported')
      return
    }

    setUploading(true)
    try {
      await documentService.uploadDocument(spaceId, file)
      success('Document uploaded and processed successfully!')
      fetchDocuments()
    } catch (e: any) {
      toastError(e?.message ?? 'Failed to upload document')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (docId: number) => {
    if (!window.confirm('Are you sure you want to delete this document?')) return
    try {
      await documentService.deleteDocument(spaceId, docId)
      success('Document deleted')
      setDocuments(docs => docs.filter(d => d.id !== docId))
    } catch (e: any) {
      toastError(e?.message ?? 'Failed to delete document')
    }
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 tab-panel-enter">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-xl font-semibold text-white mb-1">Study Materials</h2>
          <p className="text-sm text-slate-400">
            Upload PDFs or Text files for {subject}. The AI will use these to answer questions and generate quizzes.
          </p>
        </div>
        <div>
          <input
            type="file"
            ref={fileInputRef}
            className="hidden"
            accept=".pdf,.txt"
            onChange={handleFileUpload}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="btn-primary py-2 px-4 text-sm flex items-center gap-2"
          >
            {uploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Processing...
              </>
            ) : (
              <>
                <Upload className="w-4 h-4" /> Upload Material
              </>
            )}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-6 h-6 text-brand-400 animate-spin" />
        </div>
      ) : documents.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center border border-dashed border-white/10 rounded-2xl bg-white/[0.02]">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4 bg-brand-500/10 text-brand-400">
            <BookOpen className="w-8 h-8" />
          </div>
          <h3 className="text-lg font-medium text-white mb-2">No materials yet</h3>
          <p className="text-sm text-slate-400 max-w-sm mb-6">
            Upload your syllabus or reference material to enable grounded AI features.
          </p>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="btn-outline py-2 px-4 text-sm"
          >
            Choose a File
          </button>
        </div>
      ) : (
        <div className="grid gap-3">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center justify-between p-4 rounded-xl border border-white/10 bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-sm font-medium text-white">{doc.filename}</h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {doc.file_type.toUpperCase()} • Uploaded on {new Date(doc.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                className="p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                title="Delete document"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
