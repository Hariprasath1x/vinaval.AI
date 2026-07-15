import api from './api'
import type { Space, SpaceCreate, SpaceDetail, Note, NoteUpdate } from '../types/space'

export const spaceService = {
  /** Create or retrieve an existing space for (exam, subject). Returns the space. */
  async createOrGet(data: SpaceCreate): Promise<Space> {
    const res = await api.post<Space>('/spaces', data)
    return res.data
  },

  /** List all spaces for the current user. */
  async list(): Promise<Space[]> {
    const res = await api.get<Space[]>('/spaces')
    return res.data
  },

  /** Get a single space with its full message history. */
  async getById(id: number): Promise<SpaceDetail> {
    const res = await api.get<SpaceDetail>(`/spaces/${id}`)
    return res.data
  },

  /** Get the note for a space. */
  async getNote(spaceId: number): Promise<Note> {
    const res = await api.get<Note>(`/spaces/${spaceId}/note`)
    return res.data
  },

  /** Upsert the note for a space. */
  async saveNote(spaceId: number, data: NoteUpdate): Promise<Note> {
    const res = await api.put<Note>(`/spaces/${spaceId}/note`, data)
    return res.data
  },

  /**
   * Open an SSE stream for AI chat.
   * Calls onChunk with each text chunk, then onDone when complete.
   * Returns an AbortController so the caller can cancel.
   */
  streamChat(
    spaceId: number,
    content: string,
    onChunk: (chunk: string) => void,
    onDone: () => void,
    onError: (err: string) => void,
  ): AbortController {
    const controller = new AbortController()
    const token = localStorage.getItem('vinaval_token')

    fetch(`/api/v1/spaces/${spaceId}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ content }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          onError(`Server error ${response.status}`)
          return
        }
        const reader = response.body!.getReader()
        const decoder = new TextDecoder()

        while (true) {
          const { value, done } = await reader.read()
          if (done) break

          const text = decoder.decode(value, { stream: true })
          // Each SSE line: "data: <payload>\n\n"
          const lines = text.split('\n')
          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const payload = line.slice(6).trim()
            if (payload === '[DONE]') {
              onDone()
              return
            }
            if (payload) {
              try {
                const chunk = JSON.parse(payload)
                if (typeof chunk === 'object' && chunk.error) {
                  onError(chunk.error)
                } else {
                  onChunk(chunk as string)
                }
              } catch {
                // ignore malformed chunks
              }
            }
          }
        }
        onDone()
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          onError(err.message)
        }
      })

    return controller
  },
}
