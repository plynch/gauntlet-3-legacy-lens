import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from './App'
import * as api from './lib/api'

vi.mock('./lib/api', async () => {
  const actual = await vi.importActual<typeof import('./lib/api')>('./lib/api')
  return {
    ...actual,
    getHealth: vi.fn(),
    runQuery: vi.fn(),
  }
})

const getHealthMock = vi.mocked(api.getHealth)
const runQueryMock = vi.mocked(api.runQuery)

describe('App query keyboard shortcuts', () => {
  beforeEach(() => {
    getHealthMock.mockResolvedValue({
      status: 'ok',
      service: 'LegacyLens API (Test)',
      timestamp: '2026-03-04T18:00:00Z',
      qdrant_configured: true,
      openai_mode: 'openai',
      degraded_reason: null,
    })
    runQueryMock.mockResolvedValue({
      question: 'Where is file IO handled?',
      answer: 'Answer',
      insufficient_evidence: false,
      snippets: [],
      citations: [],
    })
  })

  it('submits on Enter', async () => {
    render(<App />)

    const textarea = await screen.findByLabelText(/ask about the codebase/i)
    await userEvent.type(textarea, 'Where is file IO handled?')
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter' })

    await waitFor(() => expect(runQueryMock).toHaveBeenCalledTimes(1))
    expect(runQueryMock).toHaveBeenCalledWith({ question: 'Where is file IO handled?' })
  })

  it('does not submit on Shift+Enter', async () => {
    render(<App />)

    const textarea = await screen.findByLabelText(/ask about the codebase/i)
    await userEvent.type(textarea, 'Where is file IO handled?')
    fireEvent.keyDown(textarea, { key: 'Enter', code: 'Enter', shiftKey: true })

    expect(runQueryMock).not.toHaveBeenCalled()
  })
})
