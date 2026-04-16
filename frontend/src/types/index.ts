// EntroFeed data types matching backend models

export interface Feed {
  id: string;
  name: string;
  category: string;
  type: string;
  url: string;
  preview_only: boolean;
  notify: boolean;
  refresh_enabled: boolean;
  notify_destination?: string;
  use_script?: boolean;
  retrieve_content?: boolean;
}

export interface FeedEntry {
  id: string;
  feed_id: string;
  feed_name?: string;
  title: string;
  url: string;
  published_at: string;
  updated_at: string;
  preview?: string;
  content?: string;
  authors?: string[];
  total_score?: number;
  recency_score?: number;
  authority_score?: number;
  relevance_score?: number;
  impact_score?: number;
  tags?: Tag[];
  matched_interests?: string[];
  has_ontology_match?: boolean;
  is_read?: boolean;
  liked?: number; // -1 = dislike, 0 = none, 1 = like
  is_favorite?: boolean;
}

export interface Tag {
  name: string;
  category: string;
  confidence: number;
  matched_keywords?: string[];
  is_entity?: boolean;
  is_rss_tag?: boolean;
}

export interface EntryContent {
  id: string;
  feed_id: string;
  feed_name: string;
  title: string;
  url: string;
  published_at: string;
  updated_at: string;
  byline?: string;
  preview?: string;
  content?: string;
  summary?: string;
  word_count?: number;
  reading_time?: number;
  reading_level?: number;
  unretrievable?: boolean;
  banned?: boolean;
  total_score?: number;
  recency_score?: number;
  authority_score?: number;
  relevance_score?: number;
  impact_score?: number;
  tags?: Tag[];
  matched_interests?: string[];
  has_ontology_match?: boolean;
}

export interface GlobalSettings {
  send_notification: boolean;
  theme: string;
  refresh_interval: number;
  reading_speed: number;
  notification_handler_key: string;
  llm_handler_key: string;
  content_retrieval_handler_key: string;
  recent_hours: number;
  finished_onboarding: boolean;
}

export interface Recommendation {
  entry_id: string;
  title: string;
  url: string;
  feed_name: string;
  source: 'interest' | 'trending' | 'similar';
  match_score?: number;
  similarity_score?: number;
  trending_score?: number;
  matched_interest?: string;
  priority?: number;
}

export interface UserInterest {
  id?: string;
  name: string;
  category: string;
  source: 'explicit' | 'inferred' | 'derived';
  confidence: number;
  priority: number;
  relevance_score?: number;
}

export interface Handler {
  name: string;
  type: 'llm' | 'notification' | 'content' | 'storage';
  configured: boolean;
}

export interface AboutInfo {
  version: string;
  python_version: string;
  fastapi_version: string;
  docker: boolean;
  storage_handler: string;
  github: string;
}

export type Theme =
  | 'black' | 'coffee' | 'dark' | 'fantasy' | 'forest' | 'lemonade'
  | 'lofi' | 'luxury' | 'night' | 'nord' | 'pastel' | 'synthwave' | 'winter'
  | 'entrofeed-blue';
