import api from './api'

export interface ExamSubject {
  name: string
  icon: string
  color: string
}

export interface Exam {
  id: string
  name: string
  tag: string
  description: string
  subjects: ExamSubject[]
}

export const examService = {
  async listExams(): Promise<Exam[]> {
    const { data } = await api.get<Exam[]>('/exams')
    return data
  },

  async selectExam(examId: string): Promise<{ selected_exam: string; message: string }> {
    const { data } = await api.post('/exams/select', { exam_id: examId })
    return data
  },

  async getMyExam(): Promise<{ selected_exam: string | null }> {
    const { data } = await api.get('/exams/me')
    return data
  },
}
