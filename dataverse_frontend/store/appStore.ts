import { create } from 'zustand'
import {
  ActiveFilter,
  ClarificationRequest,
  Message,
  ProactiveInsight,
  Session,
} from '@/types'

interface AppState {
  session: Session | null
  messages: Message[]
  isStreaming: boolean
  activeFilters: ActiveFilter[]
  proactiveInsights: ProactiveInsight[]
  pendingClarification: ClarificationRequest | null
  setSession: (session: Session | null) => void
  addMessage: (message: Message) => void
  setStreaming: (streaming: boolean) => void
  setActiveFilters: (filters: ActiveFilter[]) => void
  setProactiveInsights: (insights: ProactiveInsight[]) => void
  setPendingClarification: (clarification: ClarificationRequest | null) => void
  clearMessages: () => void
}

export const useAppStore = create<AppState>((set) => ({
  session: null,
  messages: [],
  isStreaming: false,
  activeFilters: [],
  proactiveInsights: [],
  pendingClarification: null,
  setSession: (session) => set({ session }),
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  setStreaming: (streaming) => set({ isStreaming: streaming }),
  setActiveFilters: (activeFilters) => set({ activeFilters }),
  setProactiveInsights: (proactiveInsights) => set({ proactiveInsights }),
  setPendingClarification: (pendingClarification) => set({ pendingClarification }),
  clearMessages: () => set({
    messages: [],
    activeFilters: [],
    proactiveInsights: [],
    pendingClarification: null,
  }),
}))
