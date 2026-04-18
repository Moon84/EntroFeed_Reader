import { apiGet } from './client'

export interface LLMModel {
  name: string
  display_name: string
  provider: string
  capabilities: string[]
  description: string
  pricing_hint: string
  context_window: number
}

export interface LLMProvider {
  id: string
  name: string
  available: boolean
  missing_env: string[]
  models: LLMModel[]
}

export interface LLMProvidersResponse {
  providers: LLMProvider[]
}

export interface LLMModelsResponse {
  models: LLMModel[]
}

export async function getLLMProviders(): Promise<LLMProvidersResponse> {
  return apiGet<LLMProvidersResponse>('/api/llm/providers')
}

export async function getLLMModels(provider?: string): Promise<LLMModelsResponse> {
  const url = provider ? `/api/llm/models?provider=${provider}` : '/api/llm/models'
  return apiGet<LLMModelsResponse>(url)
}

// Capability display names and icons
export const CAPABILITY_LABELS: Record<string, { label: string; color: string }> = {
  text: { label: 'Text', color: '#1890ff' },
  reasoning: { label: 'Reasoning', color: '#722ed1' },
  vision: { label: 'Vision', color: '#52c41a' },
  image_gen: { label: 'Image Gen', color: '#fa8c16' },
  func_call: { label: 'Function Call', color: '#f5222d' },
  code: { label: 'Code', color: '#13c2c2' },
  long_ctx: { label: 'Long Context', color: '#eb2f96' },
}

export function getCapabilityLabel(capability: string): { label: string; color: string } {
  return CAPABILITY_LABELS[capability] || { label: capability, color: '#8c8c8c' }
}
