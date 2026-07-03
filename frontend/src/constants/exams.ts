// Hardcoded exam and subject data — mirrors backend constants.py
// Only NEET and TNPSC are supported for MVP.

export interface SubjectInfo {
  name: string
  icon: string
  color: string          // used for tailwind-compatible color theming
  bgClass: string        // full tailwind bg class
  textClass: string      // full tailwind text class
  borderClass: string    // full tailwind border class
}

export interface ExamInfo {
  id: 'NEET' | 'TNPSC'
  name: string
  tag: string
  description: string
  gradient: string       // CSS gradient for card
  subjects: SubjectInfo[]
}

export const EXAMS: ExamInfo[] = [
  {
    id: 'NEET',
    name: 'NEET',
    tag: 'Medical Entrance',
    description: 'National Eligibility cum Entrance Test for undergraduate medical admissions across India.',
    gradient: 'linear-gradient(135deg, rgba(59,130,246,0.15) 0%, rgba(139,92,246,0.1) 100%)',
    subjects: [
      { name: 'Physics',   icon: '⚛️',  color: 'blue',    bgClass: 'bg-blue-500/10',    textClass: 'text-blue-400',    borderClass: 'border-blue-500/20' },
      { name: 'Chemistry', icon: '🧪',  color: 'violet',  bgClass: 'bg-violet-500/10',  textClass: 'text-violet-400',  borderClass: 'border-violet-500/20' },
      { name: 'Botany',    icon: '🌿',  color: 'emerald', bgClass: 'bg-emerald-500/10', textClass: 'text-emerald-400', borderClass: 'border-emerald-500/20' },
      { name: 'Zoology',   icon: '🦎',  color: 'amber',   bgClass: 'bg-amber-500/10',   textClass: 'text-amber-400',   borderClass: 'border-amber-500/20' },
    ],
  },
  {
    id: 'TNPSC',
    name: 'TNPSC',
    tag: 'Civil Services',
    description: 'Tamil Nadu Public Service Commission exam for state government service recruitment.',
    gradient: 'linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(6,182,212,0.1) 100%)',
    subjects: [
      { name: 'History',         icon: '🏛️',  color: 'orange', bgClass: 'bg-orange-500/10', textClass: 'text-orange-400', borderClass: 'border-orange-500/20' },
      { name: 'Geography',       icon: '🌍',  color: 'teal',   bgClass: 'bg-teal-500/10',   textClass: 'text-teal-400',   borderClass: 'border-teal-500/20' },
      { name: 'Polity',          icon: '⚖️',  color: 'indigo', bgClass: 'bg-indigo-500/10', textClass: 'text-indigo-400', borderClass: 'border-indigo-500/20' },
      { name: 'Economics',       icon: '📈',  color: 'purple', bgClass: 'bg-purple-500/10', textClass: 'text-purple-400', borderClass: 'border-purple-500/20' },
      { name: 'Science',         icon: '🔬',  color: 'cyan',   bgClass: 'bg-cyan-500/10',   textClass: 'text-cyan-400',   borderClass: 'border-cyan-500/20' },
      { name: 'Current Affairs', icon: '📰',  color: 'rose',   bgClass: 'bg-rose-500/10',   textClass: 'text-rose-400',   borderClass: 'border-rose-500/20' },
    ],
  },
]

export const EXAM_MAP: Record<string, ExamInfo> = Object.fromEntries(EXAMS.map(e => [e.id, e]))

export function getExamById(id: string): ExamInfo | undefined {
  return EXAM_MAP[id]
}
