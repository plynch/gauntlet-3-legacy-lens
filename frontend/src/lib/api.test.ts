import { afterEach, describe, expect, it } from 'vitest'
import { areIngestControlsEnabled } from './api'

type WindowWithConfig = Window &
  typeof globalThis & {
    __APP_CONFIG__?: {
      ENABLE_INGEST_CONTROLS?: string | boolean
    }
  }

const appWindow = window as WindowWithConfig

afterEach(() => {
  delete appWindow.__APP_CONFIG__
})

describe('areIngestControlsEnabled', () => {
  it('returns false when runtime config is quoted false', () => {
    appWindow.__APP_CONFIG__ = { ENABLE_INGEST_CONTROLS: '"false"' }
    expect(areIngestControlsEnabled()).toBe(false)
  })

  it('returns false when runtime config is boolean false', () => {
    appWindow.__APP_CONFIG__ = { ENABLE_INGEST_CONTROLS: false }
    expect(areIngestControlsEnabled()).toBe(false)
  })

  it('defaults to true when runtime config is absent', () => {
    expect(areIngestControlsEnabled()).toBe(true)
  })
})
