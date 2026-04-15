import { apiGet, apiPatch, apiPostJson } from './client'
import type { FeedEntry } from '../types'

export interface EntryWithFeed extends FeedEntry {
  feed_name: string;
}

export interface EntryStateUpdate {
  is_read?: boolean;
  liked?: number;
  is_favorite?: boolean;
}

export interface TranslationRequest {
  text: string;
  target_lang: string;
}

export interface TranslationResult {
  success: boolean;
  original?: { text: string; language: string };
  translation?: { text: string; language: string };
  usage?: { total_tokens: number; requests: number };
  error?: string;
}

export interface LLMStatus {
  available: boolean;
  provider: string;
  model: string;
  error?: string;
  usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    requests: number;
    limit: number;
  };
}

export async function listFeedEntries(feedId?: string): Promise<FeedEntry[]> {
  if (feedId) {
    return apiGet<FeedEntry[]>(`/util/list-feed-entries?feed_id=${feedId}`)
  }
  return apiGet<FeedEntry[]>('/util/list-feed-entries')
}

export async function getEntryContent(entryId: string): Promise<Record<string, unknown>> {
  return apiGet<Record<string, unknown>>(`/read/${entryId}?accept=json`)
}

export async function updateEntryState(entryId: string, update: EntryStateUpdate): Promise<void> {
  await apiPatch(`/api/entries/${entryId}`, update)
}

export async function translateText(text: string, targetLang: string): Promise<TranslationResult> {
  return apiPostJson<TranslationResult>('/api/translate', { text, target_lang: targetLang })
}

export async function getLLMStatus(): Promise<LLMStatus> {
  return apiGet<LLMStatus>('/api/llm/status')
}
