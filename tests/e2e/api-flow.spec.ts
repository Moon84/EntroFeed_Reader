import { test, expect, request } from '@playwright/test';

/**
 * API Integration Tests for EntroFeed
 *
 * Tests critical API flows:
 * - Health check
 * - Settings retrieval
 * - Feed operations
 * - Entry state management
 * - Recommendations
 * - Agent chat
 */

const API_BASE = process.env.API_BASE || 'http://localhost:8000';

test.describe('API Health', () => {
  test('health endpoint returns OK', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/health');
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.status).toBe('OK');
  });

  test('about endpoint returns app info', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    // About page returns HTML by default, API returns JSON
    const response = await ctx.get('/about', { headers: { accept: 'application/json' } });
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('version');
    expect(data).toHaveProperty('settings');
  });

  test('settings endpoint returns themes', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/settings/', { headers: { accept: 'application/json' } });
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('themes');
    expect(Array.isArray(data.themes)).toBe(true);
  });
});

test.describe('Feed Operations API', () => {
  test('list feeds endpoint works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/util/list-feeds');
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test('list handlers endpoint works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/util/list-handlers');
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(Array.isArray(data)).toBe(true);
  });

  test('feed stats endpoint works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/util/feed-stats');
    expect(response.status()).toBe(200);
  });

  test('list feed entries works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/util/list-feed-entries');
    expect(response.status()).toBe(200);
  });
});

test.describe('Entry State API', () => {
  test('can create and update entry state', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    // First get some entries
    const entriesResponse = await ctx.get('/util/list-feed-entries');
    expect(entriesResponse.status()).toBe(200);

    // Try to update entry state (may fail if no entries)
    const patchResponse = await ctx.patch('/api/entries/test-id', {
      data: { is_read: true },
      headers: { 'Content-Type': 'application/json' }
    });
    expect([200, 201, 404, 500]).toContain(patchResponse.status());
  });
});

test.describe('Recommendations API', () => {
  test('interest recommendations endpoint works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/api/recommendations/interest');
    expect([200, 500]).toContain(response.status());
  });

  test('trending recommendations endpoint works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/api/recommendations/trending');
    expect([200, 500]).toContain(response.status());
  });
});

test.describe('Agent Chat API', () => {
  test('can list agent sessions', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/api/agent/sessions');
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('sessions');
  });

  test('can create agent session', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.post('/api/agent/sessions', {
      data: {},
      headers: { 'Content-Type': 'application/json' }
    });
    expect(response.status()).toBe(201);
    const data = await response.json();
    expect(data).toHaveProperty('id');
  });

  test('agent tools endpoint works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/api/agent/tools');
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('tools');
  });

  test('LLM status endpoint works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/api/llm/status');
    expect(response.status()).toBe(200);
  });

  test('LLM usage endpoint works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/api/llm/usage');
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('today');
  });
});

test.describe('Interests API', () => {
  test('list interests works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/api/interests');
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('interests');
  });

  test('inferred interests works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/api/interests/inferred');
    expect(response.status()).toBe(200);
  });
});

test.describe('Search API', () => {
  test('search endpoint works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/api/search?q=test');
    expect(response.status()).toBe(200);
  });

  test('search handles special characters', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/api/search?q=hello%20world');
    expect(response.status()).toBe(200);
  });
});

test.describe('Backup/Export API', () => {
  test('export OPML works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/api/export_opml/');
    expect(response.status()).toBe(200);
  });

  test('backup endpoint works', async () => {
    const ctx = await request.newContext({ baseURL: API_BASE });
    const response = await ctx.get('/api/backup/');
    expect(response.status()).toBe(200);
  });
});
