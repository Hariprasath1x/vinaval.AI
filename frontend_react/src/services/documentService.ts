import api from './api'

export interface SpaceDocument {
  id: number
  filename: string
  file_type: string
  created_at: string
}

export const documentService = {
  async uploadDocument(spaceId: number, file: File): Promise<SpaceDocument> {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await api.post<SpaceDocument>(`/spaces/${spaceId}/documents`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  },

  async listDocuments(spaceId: number): Promise<SpaceDocument[]> {
    const { data } = await api.get<SpaceDocument[]>(`/spaces/${spaceId}/documents`)
    return data
  },

  async deleteDocument(spaceId: number, docId: number): Promise<void> {
    await api.delete(`/spaces/${spaceId}/documents/${docId}`)
  },
}
