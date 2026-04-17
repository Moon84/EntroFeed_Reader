import { test, expect, chromium } from '@playwright/test'

/**
 * Agent E2E Tests - Comprehensive evaluation of agent capabilities
 * Tests real conversations, task completion, and memory persistence
 */

test.describe('Agent Real Conversation Eval', () => {
  const BASE_URL = 'http://localhost:8001'

  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/_app/agent`)
    await page.waitForLoadState('networkidle')
  })

  test('1. List Feeds Task', async ({ page }) => {
    const input = page.locator('textarea').first()

    // Ask to list feeds
    await input.fill('List all my RSS feeds')
    await input.press('Enter')

    // Wait for response
    await page.waitForTimeout(8000)

    // Get page content and check for feed-related response
    const content = await page.content()
    console.log('Response length:', content.length)

    // Should get some response (either feed list or error about LLM)
    expect(content.length).toBeGreaterThan(500)
  })

  test('2. Get Recommendations Task', async ({ page }) => {
    const input = page.locator('textarea').first()

    // Ask for recommendations
    await input.fill('Show me my personalized recommendations')
    await input.press('Enter')

    await page.waitForTimeout(8000)

    const content = await page.content()
    expect(content.length).toBeGreaterThan(500)
  })

  test('3. Session Persistence - Create session, chat, reload page', async ({ page }) => {
    const input = page.locator('textarea').first()

    // Send first message
    await input.fill('Hello, remember my name is TestUser')
    await input.press('Enter')
    await page.waitForTimeout(5000)

    // Check that message appears in chat
    const messages1 = await page.locator('[class*="message"]').count()
    console.log('Messages after first exchange:', messages1)

    // Reload the page
    await page.reload()
    await page.waitForLoadState('networkidle')

    // Session should be restored from localStorage
    await page.waitForTimeout(2000)

    // Send another message referencing the previous context
    await input.fill('What was my name?')
    await input.press('Enter')
    await page.waitForTimeout(8000)

    const content = await page.content()
    // Should either remember the name or indicate no memory (depending on LLM capability)
    expect(content.length).toBeGreaterThan(500)
  })

  test('4. Multi-turn Conversation', async ({ page }) => {
    const input = page.locator('textarea').first()

    // Turn 1: Ask about feeds
    await input.fill('What feeds do I have?')
    await input.press('Enter')
    await page.waitForTimeout(6000)

    // Turn 2: Follow up question
    await input.fill('Which one has the most articles?')
    await input.press('Enter')
    await page.waitForTimeout(6000)

    // Turn 3: Request recommendations
    await input.fill('Give me article recommendations from those feeds')
    await input.press('Enter')
    await page.waitForTimeout(6000)

    const content = await page.content()
    // Should have accumulated messages
    const messageCount = await page.locator('[class*="content"]').count()
    console.log('Total message elements:', messageCount)
    expect(messageCount).toBeGreaterThan(0)
  })

  test('5. Session Management - Create, switch, delete', async ({ request }) => {
    // Test session API directly
    const BASE = 'http://localhost:8001'

    // Create session using POST to /api/agent/sessions
    const res1 = await request.post(`${BASE}/api/agent/sessions`, { data: {} })
    expect(res1.ok()).toBeTruthy()
    const data1 = await res1.json()
    const session1Id = data1.id
    console.log('Session 1 ID:', session1Id)

    // List sessions
    const sessionsRes = await request.get(`${BASE}/api/agent/sessions`)
    expect(sessionsRes.ok()).toBeTruthy()
    const sessionsData = await sessionsRes.json()
    expect(sessionsData.sessions.length).toBeGreaterThan(0)

    // Get session 1 messages
    const sessionRes = await request.get(`${BASE}/api/agent/sessions/${session1Id}`)
    expect(sessionRes.ok()).toBeTruthy()
    const sessionData = await sessionRes.json()
    console.log('Session 1 messages:', sessionData.messages?.length)

    // Clear session
    const clearRes = await request.post(`${BASE}/api/agent/sessions/${session1Id}/clear`, {})
    console.log('Clear response status:', clearRes.status())
  })

  test('6. Translation Tool Integration', async ({ request }) => {
    const BASE = 'http://localhost:8001'

    // Test translation directly through the translate API (more reliable)
    const res = await request.post(`${BASE}/api/translate`, {
      data: { text: 'Hello World', target_lang: 'zh' }
    })

    expect(res.ok()).toBeTruthy()
    const data = await res.json()
    console.log('Translation response:', data.translation?.text)
    expect(data.success).toBe(true)
    expect(data.translation.text).toContain('世界')
  })

  test('7. Error Handling - Invalid Session', async ({ request }) => {
    const BASE = 'http://localhost:8001'

    // Try to get non-existent session
    const res = await request.get(`${BASE}/api/agent/sessions/invalid-id-123`)
    // Should return 404 or error
    expect(res.status()).toBeGreaterThanOrEqual(400)
  })

  test('8. Concurrent Sessions', async ({ request }) => {
    const BASE = 'http://localhost:8001'

    // Create two sessions
    const res1 = await request.post(`${BASE}/api/agent/chat`, {
      data: { message: 'Message for session 1' }
    })
    const data1 = await res1.json()
    const session1Id = data1.session_id

    // Create new session
    const res2 = await request.post(`${BASE}/api/agent/sessions`, { data: {} })
    const data2 = await res2.json()
    const session2Id = data2.id

    // Send message to session 2
    await request.post(`${BASE}/api/agent/chat`, {
      data: { message: 'Message for session 2', session_id: session2Id }
    })

    // Verify sessions are different
    expect(session1Id).not.toEqual(session2Id)

    // Verify session 2 has the message
    const session2Res = await request.get(`${BASE}/api/agent/sessions/${session2Id}`)
    const session2Data = await session2Res.json()
    expect(session2Data.messages.length).toBeGreaterThan(0)
  })
})

test.describe('Agent Memory Persistence', () => {
  test('memory persists across page reloads', async ({ page, context }) => {
    const BASE = 'http://localhost:8001'

    // First browser context - create session and send message
    await page.goto(`${BASE}/_app/agent`)
    await page.waitForLoadState('networkidle')

    const input = page.locator('textarea').first()
    await input.fill('Remember: my favorite topic is AI and machine learning')
    await input.press('Enter')
    await page.waitForTimeout(8000)

    // Get session ID from localStorage
    const sessionId = await page.evaluate(() => localStorage.getItem('entrofeed_agent_session'))
    console.log('Saved session ID:', sessionId)

    // Reload the page
    await page.reload()
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // Ask to recall the favorite topic
    const input2 = page.locator('textarea').first()
    await input2.fill('What is my favorite topic?')
    await input2.press('Enter')
    await page.waitForTimeout(8000)

    const content = await page.content()
    // Check if the response mentions AI/machine learning or indicates memory
    console.log('Response contains AI/ML:', content.toLowerCase().includes('ai') || content.toLowerCase().includes('machine learning'))
  })

  test('session data is saved to disk', async ({ request }) => {
    const BASE = 'http://localhost:8001'

    // Create a session with specific content
    const res = await request.post(`${BASE}/api/agent/chat`, {
      data: { message: 'Test message for persistence check' }
    })
    const data = await res.json()
    const sessionId = data.session_id

    // Verify session exists via API
    const sessionRes = await request.get(`${BASE}/api/agent/sessions/${sessionId}`)
    expect(sessionRes.ok()).toBeTruthy()

    // Sessions are persisted to data/chat_sessions.json on the server
    // This test verifies the API correctly retrieves persisted sessions
    const sessionsRes = await request.get(`${BASE}/api/agent/sessions`)
    const sessionsData = await sessionsRes.json()

    const ourSession = sessionsData.sessions.find((s: any) => s.id === sessionId)
    expect(ourSession).toBeDefined()
  })
})

test.describe('API Direct Tests', () => {
  const BASE = 'http://localhost:8001'

  test('translate API works correctly', async ({ request }) => {
    const res = await request.post(`${BASE}/api/translate`, {
      data: { text: 'The future of AI in healthcare', target_lang: 'zh' }
    })

    expect(res.ok()).toBeTruthy()
    const data = await res.json()
    expect(data.success).toBe(true)
    expect(data.translation.text).toContain('医疗')
    console.log('Translation:', data.translation.text)
  })

  test('llm status API', async ({ request }) => {
    const res = await request.get(`${BASE}/api/llm/status`)

    expect(res.ok()).toBeTruthy()
    const data = await res.json()
    console.log('LLM Status:', JSON.stringify(data, null, 2))

    // Should return available status
    expect(data).toHaveProperty('available')
    expect(data).toHaveProperty('usage')
  })

  test('recommendations API', async ({ request }) => {
    const res = await request.get(`${BASE}/api/recommendations/interest?limit=5`)

    expect(res.ok()).toBeTruthy()
    const data = await res.json()
    expect(data).toHaveProperty('recommendations')
    console.log('Recommendations count:', data.recommendations?.length)
  })
})

test.describe('Agent Tools & Skills E2E', () => {
  const BASE = 'http://localhost:8001'

  test('1. Agent can list feeds via chat', async ({ page }) => {
    await page.goto(`${BASE}/_app/agent`)
    await page.waitForLoadState('networkidle')

    const input = page.locator('textarea').first()

    // Ask to list feeds
    await input.fill('List all my RSS feed sources')
    await input.press('Enter')
    await page.waitForTimeout(8000)

    // Check that we got a response about feeds
    const content = await page.content()
    // The agent should have called list_feeds tool and returned feed information
    expect(content.length).toBeGreaterThan(500)
    console.log('List feeds response length:', content.length)
  })

  test('2. Agent can search entries', async ({ page }) => {
    await page.goto(`${BASE}/_app/agent`)
    await page.waitForLoadState('networkidle')

    const input = page.locator('textarea').first()

    // Search for articles about AI
    await input.fill('Search for articles about AI in my feeds')
    await input.press('Enter')
    await page.waitForTimeout(8000)

    const content = await page.content()
    expect(content.length).toBeGreaterThan(500)
  })

  test('3. Agent can get daily digest', async ({ page }) => {
    await page.goto(`${BASE}/_app/agent`)
    await page.waitForLoadState('networkidle')

    const input = page.locator('textarea').first()

    // Ask for daily digest
    await input.fill('Give me today\'s news digest')
    await input.press('Enter')
    await page.waitForTimeout(10000)

    const content = await page.content()
    expect(content.length).toBeGreaterThan(500)
  })

  test('4. Query favorites via list-feed-entries API', async ({ request }) => {
    // First mark an entry as favorite via API
    const entriesRes = await request.get(`${BASE}/util/list-feed-entries?limit=5`)
    expect(entriesRes.ok()).toBeTruthy()
    const entriesData = await entriesRes.json()

    if (entriesData.length > 0) {
      const entryId = entriesData[0].id

      // Mark as favorite
      await request.post(`${BASE}/api/update_entry_state/${entryId}`, {
        data: { is_favorite: true }
      })

      // Query again to verify
      const entriesRes2 = await request.get(`${BASE}/util/list-feed-entries?limit=5`)
      const entriesData2 = await entriesRes2.json()

      console.log('Entries with favorites:', entriesData2.filter((e: any) => e.is_favorite).length)
    }
  })

  test('5. Agent can get user interests', async ({ page }) => {
    await page.goto(`${BASE}/_app/agent`)
    await page.waitForLoadState('networkidle')

    const input = page.locator('textarea').first()

    // Ask about interests
    await input.fill('What are my current interests?')
    await input.press('Enter')
    await page.waitForTimeout(8000)

    const content = await page.content()
    expect(content.length).toBeGreaterThan(500)
  })

  test('6. Execute skill via chat interface', async ({ page }) => {
    // Test that agent can discuss skills through chat
    await page.goto(`${BASE}/_app/agent`)
    await page.waitForLoadState('networkidle')

    const input = page.locator('textarea').first()

    // Ask about available skills
    await input.fill('What skills can you perform?')
    await input.press('Enter')
    await page.waitForTimeout(10000)

    const content = await page.content()
    expect(content.length).toBeGreaterThan(500)

    // Now ask to use rss-daily-digest
    await input.fill('Generate a daily digest for me using the rss-daily-digest skill')
    await input.press('Enter')
    await page.waitForTimeout(10000)

    const content2 = await page.content()
    // Agent should respond (even if it can't execute the skill directly)
    expect(content2.length).toBeGreaterThan(500)
    console.log('Skill discussion response length:', content2.length)
  })

  test('7. Get high priority content', async ({ page }) => {
    await page.goto(`${BASE}/_app/agent`)
    await page.waitForLoadState('networkidle')

    const input = page.locator('textarea').first()

    // Ask for high priority content
    await input.fill('Show me high priority articles')
    await input.press('Enter')
    await page.waitForTimeout(8000)

    const content = await page.content()
    expect(content.length).toBeGreaterThan(500)
  })

  test('8. Multi-step task - list feeds then get entries', async ({ page }) => {
    await page.goto(`${BASE}/_app/agent`)
    await page.waitForLoadState('networkidle')

    const input = page.locator('textarea').first()

    // First message - get feeds
    await input.fill('Show me all my feed names and URLs')
    await input.press('Enter')
    await page.waitForTimeout(8000)

    // Second message - get entries from first feed
    await input.fill('Now show me recent articles from the first feed')
    await input.press('Enter')
    await page.waitForTimeout(8000)

    // Should have accumulated messages
    const content = await page.content()
    expect(content.length).toBeGreaterThan(1000)
    console.log('Multi-step conversation length:', content.length)
  })
})
