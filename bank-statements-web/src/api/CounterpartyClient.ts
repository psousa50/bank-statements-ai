import { axiosInstance } from './ApiClient'
import { Counterparty, CounterpartyType } from '../types/Counterparty'

export type { Counterparty }

export interface CounterpartyListResponse {
  counterparties: Counterparty[]
  total: number
}

export interface CounterpartyUploadResponse {
  counterparties: Counterparty[]
  total: number
  created: number
  updated: number
}

export interface CounterpartyClient {
  getAll: () => Promise<Counterparty[]>
  getById: (id: string) => Promise<Counterparty>
  createCounterparty: (name: string, type: CounterpartyType) => Promise<Counterparty>
  updateCounterparty: (id: string, name: string, type: CounterpartyType) => Promise<Counterparty>
  deleteCounterparty: (id: string) => Promise<void>
  exportCounterparties: () => Promise<void>
  uploadCounterparties: (file: File) => Promise<CounterpartyUploadResponse>
}

const BASE_URL = import.meta.env.VITE_API_URL || ''
const API_URL = `${BASE_URL}/api/v1/counterparties`

export const counterpartyClient: CounterpartyClient = {
  getAll: async (): Promise<Counterparty[]> => {
    const response = await axiosInstance.get<CounterpartyListResponse>(API_URL)
    return response.data.counterparties
  },

  getById: async (id: string): Promise<Counterparty> => {
    const response = await axiosInstance.get<Counterparty>(`${API_URL}/${id}`)
    return response.data
  },

  createCounterparty: async (name: string, type: CounterpartyType): Promise<Counterparty> => {
    const response = await axiosInstance.post<Counterparty>(API_URL, { name, type })
    return response.data
  },

  updateCounterparty: async (id: string, name: string, type: CounterpartyType): Promise<Counterparty> => {
    const response = await axiosInstance.put<Counterparty>(`${API_URL}/${id}`, { name, type })
    return response.data
  },

  deleteCounterparty: async (id: string): Promise<void> => {
    await axiosInstance.delete(`${API_URL}/${id}`)
  },

  exportCounterparties: async (): Promise<void> => {
    const response = await axiosInstance.get(`${API_URL}/export`, { responseType: 'blob' })
    const blob = new Blob([response.data], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    const contentDisposition = response.headers['content-disposition']
    const filename = contentDisposition
      ? contentDisposition.split('filename=')[1]?.replace(/"/g, '')
      : `counterparties-${new Date().toISOString().split('T')[0]}.csv`
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  },

  uploadCounterparties: async (file: File): Promise<CounterpartyUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await axiosInstance.post<CounterpartyUploadResponse>(`${API_URL}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },
}
