export interface Space {
  id: number
  exam_id: string
  subject: string
  title: string
  created_at: string
  updated_at: string
}

export interface SpaceDetail extends Space {
  messages: Message[]
}

export interface Message {
  id: number
  space_id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface Note {
  space_id: number
  content: string
  updated_at?: string
}

export interface SpaceCreate {
  exam_id: string
  subject: string
}

export interface MessageCreate {
  content: string
}

export interface NoteUpdate {
  content: string
}
