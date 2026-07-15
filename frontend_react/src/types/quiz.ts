export interface QuizQuestion {
  id: number
  space_id: number
  topic: string
  question: string
  option_a: string
  option_b: string
  option_c: string
  option_d: string
  correct_option: string
  explanation: string | null
  created_at: string
}

export interface AnswerResult {
  question_id: number
  user_answer: string
  correct_option: string
  is_correct: boolean
  explanation: string | null
}

export interface SpaceStats {
  total_practice: number
  correct_practice: number
  accuracy_practice: number
  total_exam: number
  correct_exam: number
  accuracy_exam: number
  total_all: number
  correct_all: number
  accuracy_all: number
  topics_practiced: string[]
}

export interface GenerateRequest {
  topic: string
  count: number
}

export interface SubmitAnswerRequest {
  question_id: number
  user_answer: string
  time_taken_seconds?: number
  is_exam: boolean
}
