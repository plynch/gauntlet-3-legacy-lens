import { useState } from 'react'

type QueryPreset = {
  label: string
  query: string
}

const QUERY_PRESETS: QueryPreset[] = [
  { label: 'File I/O ownership', query: 'Where is file I/O handled in this codebase?' },
  { label: 'Compiler entry point', query: 'What is the main entry point for cobc?' },
  { label: 'CLI option parsing', query: 'Which modules parse compiler command-line options?' },
  { label: 'Failed open handling', query: 'Show error handling flow for failed file opens.' },
  { label: 'Copybook resolution', query: 'Where are copybooks resolved and loaded?' },
  { label: 'Symbol table writes', query: 'Which code paths create or modify symbol tables?' },
  {
    label: 'Runtime bootstrap',
    query: 'How does the runtime initialize before executing user code?',
  },
  { label: 'Numeric conversion calls', query: 'Find call sites related to numeric conversion routines.' },
  { label: 'Generated C interaction', query: 'What components interact with generated C output?' },
  {
    label: 'Compiler diagnostics',
    query: 'Show logging or diagnostics pathways used during compilation.',
  },
]

type QueryPresetsProps = {
  onSelectQuery: (query: string) => void
  disabled: boolean
}

export function QueryPresets(props: QueryPresetsProps) {
  const { disabled, onSelectQuery } = props
  const [visible, setVisible] = useState(true)

  return (
    <section className="query-presets" aria-label="Demo query presets">
      <div className="query-presets-header">
        <strong>Demo query presets (10)</strong>
        <button type="button" className="secondary-button" onClick={() => setVisible((state) => !state)}>
          {visible ? 'Hide examples' : 'Show examples'}
        </button>
      </div>

      {visible ? (
        <div className="query-presets-grid">
          {QUERY_PRESETS.map((preset, index) => (
            <button
              key={preset.label}
              type="button"
              className="query-preset-button"
              onClick={() => onSelectQuery(preset.query)}
              disabled={disabled}
            >
              <span className="query-preset-index">{index + 1}</span>
              <span>{preset.label}</span>
            </button>
          ))}
        </div>
      ) : (
        <p className="muted-note">Examples hidden. Click &quot;Show examples&quot; to bring them back.</p>
      )}
    </section>
  )
}
