import api from './api'

export interface Flashcard {
  id: number
  space_id: number
  topic: string
  front: string
  back: string
  created_at: string
}

export interface GenerateFlashcardsRequest {
  topic: string
  count?: number
}

export const flashcardService = {
  /** Generate AI flashcards for a topic. */
  async generate(spaceId: number, data: GenerateFlashcardsRequest): Promise<Flashcard[]> {
    const res = await api.post<Flashcard[]>(`/spaces/${spaceId}/flashcards/generate`, data)
    return res.data
  },

  /** List all flashcards for a space, optionally filtered by topic. */
  async list(spaceId: number, topic?: string): Promise<Flashcard[]> {
    const res = await api.get<Flashcard[]>(`/spaces/${spaceId}/flashcards`, {
      params: topic ? { topic } : undefined,
    })
    return res.data
  },

  /** Get distinct topics that have flashcards in this space. */
  async getTopics(spaceId: number): Promise<string[]> {
    const res = await api.get<string[]>(`/spaces/${spaceId}/flashcards/topics`)
    return res.data
  },

  /** Delete all flashcards for a specific topic. */
  async deleteTopic(spaceId: number, topic: string): Promise<void> {
    await api.delete(`/spaces/${spaceId}/flashcards/${encodeURIComponent(topic)}`)
  },
}
