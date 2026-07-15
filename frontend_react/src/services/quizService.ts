import api from './api'
import type {
  QuizQuestion,
  AnswerResult,
  SpaceStats,
  GenerateRequest,
  SubmitAnswerRequest,
} from '../types/quiz'

export const quizService = {
  async generate(spaceId: number, req: GenerateRequest): Promise<QuizQuestion[]> {
    const res = await api.post<QuizQuestion[]>(`/spaces/${spaceId}/quiz/generate`, req)
    return res.data
  },

  async listQuestions(spaceId: number, topic?: string): Promise<QuizQuestion[]> {
    const params = topic ? { topic } : {}
    const res = await api.get<QuizQuestion[]>(`/spaces/${spaceId}/quiz/questions`, { params })
    return res.data
  },

  async submitAnswer(spaceId: number, req: SubmitAnswerRequest): Promise<AnswerResult> {
    const res = await api.post<AnswerResult>(`/spaces/${spaceId}/quiz/attempt`, req)
    return res.data
  },

  async getStats(spaceId: number): Promise<SpaceStats> {
    const res = await api.get<SpaceStats>(`/spaces/${spaceId}/quiz/stats`)
    return res.data
  },
}
