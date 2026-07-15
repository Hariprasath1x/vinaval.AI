import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Loader2, Bot, User as UserIcon, AlertCircle, Sparkles } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Message } from '../../types/space'
import { spaceService } from '../../services/spaceService'

interface LearnTabProps {
  spaceId: number
  initialMessages: Message[]
  subject: string
  examId: string
}

export default function LearnTab({ spaceId, initialMessages, subject, examId }: LearnTabProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  // Auto-scroll to bottom whenever messages or streaming content changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  // Auto-resize textarea
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`
  }

  const sendMessage = useCallback(async () => {
    const trimmed = input.trim()
    if (!trimmed || isStreaming) return

    setInput('')
    setError(null)
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

    // Optimistically add user message to UI
    const tempUserMsg: Message = {
      id: Date.now(),
      space_id: spaceId,
      role: 'user',
      content: trimmed,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])
    setIsStreaming(true)
    setStreamingContent('')

    let fullContent = ''

    abortRef.current = spaceService.streamChat(
      spaceId,
      trimmed,
      // onChunk
      (chunk) => {
        fullContent += chunk
        setStreamingContent(fullContent)
      },
      // onDone
      () => {
        const assistantMsg: Message = {
          id: Date.now() + 1,
          space_id: spaceId,
          role: 'assistant',
          content: fullContent,
          created_at: new Date().toISOString(),
        }
        setMessages((prev) => [...prev, assistantMsg])
        setStreamingContent('')
        setIsStreaming(false)
        abortRef.current = null
      },
      // onError
      (err) => {
        setError(err)
        setStreamingContent('')
        setIsStreaming(false)
        abortRef.current = null
      },
    )
  }, [input, isStreaming, spaceId])

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const stopStreaming = () => {
    abortRef.current?.abort()
    abortRef.current = null
    setIsStreaming(false)
    setStreamingContent('')
  }

  const isEmptyState = messages.length === 0 && !isStreaming

  return (
    <div className="flex flex-col h-full" style={{ minHeight: '0' }}>

      {/* ── Messages area ── */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6 scroll-smooth">

        {isEmptyState && (
          <EmptyState subject={subject} examId={examId} onSuggestion={(s) => {
            setInput(s)
            textareaRef.current?.focus()
          }} />
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {/* Streaming bubble */}
        {isStreaming && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1"
                 style={{ backgroundColor: 'var(--accent-soft)', border: '1px solid rgba(90,127,245,0.2)' }}>
              <Bot className="w-4 h-4" style={{ color: 'var(--accent)' }} />
            </div>
            <div className="flex-1 max-w-[85%]">
              <div className="glass-card rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-200 leading-relaxed">
                {streamingContent ? (
                  <MarkdownContent content={streamingContent} />
                ) : (
                  <div className="flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: 'var(--accent)', animationDelay: '0ms' }} />
                    <span className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: 'var(--accent)', animationDelay: '150ms' }} />
                    <span className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: 'var(--accent)', animationDelay: '300ms' }} />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* ── Input area ── */}
      <div className="flex-shrink-0 px-4 py-4" style={{ borderTop: '1px solid var(--border)', backgroundColor: 'var(--bg-surface)' }}>
        <div className="max-w-4xl mx-auto">
          <div className="flex items-end gap-3 rounded-2xl px-4 py-3" style={{ backgroundColor: 'var(--bg)', border: '1px solid var(--border)' }}>
            <textarea
              ref={textareaRef}
              id="chat-input"
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={`Ask anything about ${subject}…`}
              rows={1}
              className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 resize-none outline-none leading-6 max-h-40"
              disabled={isStreaming}
            />
            <button
              id={isStreaming ? 'stop-btn' : 'send-btn'}
              onClick={isStreaming ? stopStreaming : sendMessage}
              disabled={!isStreaming && !input.trim()}
              className={`
                flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200
                ${isStreaming
                  ? 'bg-red-500/20 border border-red-500/40 text-red-400 hover:bg-red-500/30'
                  : input.trim()
                    ? 'text-white'
                    : 'bg-white/5 text-slate-600 cursor-not-allowed'
                }
              `}
              style={(!isStreaming && input.trim()) ? { backgroundColor: 'var(--accent)' } : undefined}
              title={isStreaming ? 'Stop generating' : 'Send message (Enter)'}
            >
              {isStreaming ? (
                <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: 'var(--red)' }} />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </div>
          <p className="text-center text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
            Press <kbd className="px-1 py-0.5 rounded" style={{ backgroundColor: 'var(--bg-elevated)' }}>Enter</kbd> to send · <kbd className="px-1 py-0.5 rounded" style={{ backgroundColor: 'var(--bg-elevated)' }}>Shift+Enter</kbd> for new line
          </p>
        </div>
      </div>
    </div>
  )
}

// ── Sub-components ──────────────────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  if (isUser) {
    return (
      <div className="flex gap-3 justify-end">
        <div className="max-w-[85%]">
          <div className="px-4 py-3 rounded-2xl rounded-tr-sm text-sm text-white leading-relaxed"
            style={{ backgroundColor: 'var(--accent)' }}>
            {message.content}
          </div>
        </div>
        <div className="w-8 h-8 rounded-full border flex items-center justify-center flex-shrink-0 mt-1"
             style={{ backgroundColor: 'var(--bg-elevated)', borderColor: 'var(--border)' }}>
          <UserIcon className="w-4 h-4" style={{ color: 'var(--text)' }} />
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3">
      <div className="w-8 h-8 rounded-full border flex items-center justify-center flex-shrink-0 mt-1"
           style={{ backgroundColor: 'var(--accent-soft)', borderColor: 'rgba(90,127,245,0.2)' }}>
        <Bot className="w-4 h-4" style={{ color: 'var(--accent)' }} />
      </div>
      <div className="flex-1 max-w-[85%]">
        <div className="glass-card rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-slate-200 leading-relaxed">
          <MarkdownContent content={message.content} />
        </div>
      </div>
    </div>
  )
}

function MarkdownContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => <h1 className="text-lg font-bold text-white mb-2 mt-3 first:mt-0">{children}</h1>,
        h2: ({ children }) => <h2 className="text-base font-bold text-white mb-2 mt-3 first:mt-0">{children}</h2>,
        h3: ({ children }) => <h3 className="text-sm font-bold text-slate-100 mb-1 mt-2 first:mt-0">{children}</h3>,
        p: ({ children }) => <p className="mb-2 last:mb-0 text-slate-200">{children}</p>,
        ul: ({ children }) => <ul className="list-disc list-inside mb-2 space-y-1 text-slate-200">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-1 text-slate-200">{children}</ol>,
        li: ({ children }) => <li className="text-slate-200">{children}</li>,
        strong: ({ children }) => <strong className="text-white font-semibold">{children}</strong>,
        em: ({ children }) => <em className="text-slate-300">{children}</em>,
        code: ({ className, children, ...props }) => {
          const isBlock = className?.includes('language-')
          return isBlock ? (
            <code className="block bg-black/30 rounded-lg p-3 text-xs text-emerald-300 overflow-x-auto my-2 font-mono" {...props}>
              {children}
            </code>
          ) : (
            <code className="bg-black/30 rounded px-1.5 py-0.5 text-xs text-emerald-300 font-mono" {...props}>
              {children}
            </code>
          )
        },
        blockquote: ({ children }) => (
          <blockquote className="border-l-2 border-brand-500/50 pl-3 italic text-slate-400 my-2">{children}</blockquote>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  )
}

interface EmptyStateProps {
  subject: string
  examId: string
  onSuggestion: (text: string) => void
}

function EmptyState({ subject, examId, onSuggestion }: EmptyStateProps) {
  const suggestions = getSuggestions(examId, subject)

  return (
    <div className="flex flex-col items-center justify-center py-10 px-4">
      <div className="w-16 h-16 rounded-2xl border flex items-center justify-center mb-5"
           style={{ backgroundColor: 'var(--accent-soft)', borderColor: 'rgba(90,127,245,0.2)' }}>
        <Sparkles className="w-8 h-8" style={{ color: 'var(--accent)' }} />
      </div>
      <h2 className="text-xl font-semibold text-white mb-2">
        Your {subject} AI Tutor
      </h2>
      <p className="text-slate-400 text-sm text-center max-w-sm mb-8">
        Ask me anything about {examId} {subject}. I'll explain concepts, solve problems, and help you revise.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-xl">
        {suggestions.map((s) => (
          <button
            key={s}
            onClick={() => onSuggestion(s)}
            className="text-left text-sm text-slate-300 px-4 py-3 rounded-xl hover:text-white transition-all duration-200 leading-snug"
            style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}

function getSuggestions(examId: string, subject: string): string[] {
  const map: Record<string, Record<string, string[]>> = {
    NEET: {
      Physics: [
        'Explain the concept of Newton\'s laws with examples',
        'How does a transformer work?',
        'What is the difference between series and parallel circuits?',
        'Explain Doppler effect with real-world applications',
      ],
      Chemistry: [
        'What are the types of chemical bonds?',
        'Explain periodic trends in the periodic table',
        'How does hybridisation work in organic chemistry?',
        'What is Le Chatelier\'s principle?',
      ],
      Botany: [
        'Explain the process of photosynthesis step by step',
        'What is the difference between mitosis and meiosis?',
        'Describe the structure of a plant cell',
        'What are the different types of plant tissues?',
      ],
      Zoology: [
        'Explain the human digestive system',
        'What is the difference between DNA and RNA?',
        'Describe the process of respiration in humans',
        'What are the types of neurons and their functions?',
      ],
    },
    TNPSC: {
      History: [
        'Summarise the important events of the Indian freedom movement',
        'Who were the major rulers of the Chola dynasty?',
        'Explain the significance of the 1857 revolt',
        'What were the social reform movements in Tamil Nadu?',
      ],
      Geography: [
        'Describe the major rivers of India',
        'What are the types of soil found in India?',
        'Explain India\'s climate zones',
        'What are the major industries in Tamil Nadu?',
      ],
      Polity: [
        'Explain the fundamental rights in the Indian Constitution',
        'What are the functions of the Election Commission of India?',
        'Describe the structure of the Indian Parliament',
        'What is the role of the Governor in a state?',
      ],
      Economics: [
        'What is GDP and how is it calculated?',
        'Explain the differences between fiscal and monetary policy',
        'What are the major five-year plan objectives?',
        'Describe the green revolution and its impact',
      ],
      Science: [
        'Explain Newton\'s laws of motion',
        'What is photosynthesis and why is it important?',
        'Describe the structure of an atom',
        'What are renewable and non-renewable energy sources?',
      ],
      'Current Affairs': [
        'What are the major government schemes launched recently?',
        'Explain India\'s foreign policy priorities',
        'What are the recent developments in space technology in India?',
        'Describe the major economic reforms in India',
      ],
    },
  }

  return (
    map[examId]?.[subject] ?? [
      `Explain the basics of ${subject}`,
      `What are the most important topics in ${subject} for ${examId}?`,
      `Give me a study plan for ${subject}`,
      `What are common mistakes students make in ${subject}?`,
    ]
  )
}
