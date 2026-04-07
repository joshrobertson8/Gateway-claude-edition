import { useEffect, useRef, useState } from 'react'
import Editor from '@monaco-editor/react'
import ReactMarkdown from 'react-markdown'
import { api } from '../api.js'
import { initPythonLsp, runPython } from '../pythonLsp.js'

export default function Workspace({ session, onFinish }) {
  const { submissionId, problems } = session
  const [idx, setIdx] = useState(0)
  const current = problems[idx]
  const isLast = idx === problems.length - 1

  const [code, setCode] = useState('')
  const [output, setOutput] = useState(null)
  const [running, setRunning] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [feedback, setFeedback] = useState('')
  const [hint, setHint] = useState('')
  const [hinting, setHinting] = useState(false)
  const [error, setError] = useState('')
  const alive = useRef(true)
  const editorRef = useRef(null)
  const monacoRef = useRef(null)
  const lspRef = useRef(null)
  const lintTimer = useRef(null)
  useEffect(() => {
    alive.current = true
    return () => { alive.current = false }
  }, [])

  function handleEditorMount(editor, monaco) {
    editorRef.current = editor
    monacoRef.current = monaco
    initPythonLsp(monaco).then((lsp) => {
      if (!alive.current) return
      lspRef.current = lsp
      const model = editor.getModel()
      if (model) lsp.lint(model)
    }).catch(() => {})
  }

  useEffect(() => {
    if (!lspRef.current || !editorRef.current) return
    clearTimeout(lintTimer.current)
    lintTimer.current = setTimeout(() => {
      const model = editorRef.current?.getModel()
      if (model) lspRef.current.lint(model)
    }, 350)
    return () => clearTimeout(lintTimer.current)
  }, [code])

  useEffect(() => {
    setCode(current.problemText)
    setOutput(null)
    setFeedback('')
    setHint('')
    setError('')
  }, [current.id])

  async function run() {
    setRunning(true); setError('')
    try {
      const res = await runPython(code)
      if (alive.current) setOutput(res)
    } catch (e) { if (alive.current) setError(e.message) }
    if (alive.current) setRunning(false)
  }

  async function submit() {
    setSubmitting(true); setError(''); setFeedback('')
    try {
      const r = await api.submitResponse(submissionId, current.id, code)
      if (!alive.current) return
      setFeedback(r.aiFeedback || '(no feedback)')
    } catch (e) { if (alive.current) setError(e.message) }
    if (alive.current) setSubmitting(false)
  }

  async function getHint() {
    setHinting(true); setError('')
    try {
      const { hint } = await api.hint(current.problemText, code)
      if (alive.current) setHint(hint)
    } catch (e) { if (alive.current) setError(e.message) }
    if (alive.current) setHinting(false)
  }

  async function next() {
    if (isLast) {
      try {
        await api.generateReport(submissionId)
        if (!alive.current) return
        onFinish(submissionId)
      } catch (e) { if (alive.current) setError(e.message) }
    } else {
      setIdx(idx + 1)
    }
  }

  const rightTitle = feedback ? 'Review' : hint ? 'Hint' : 'Brief'

  return (
    <main className="workspace">
      <section className="panel ide">
        <header className="panel-header">
          <div className="problem-rail">
            {problems.map((p, i) => (
              <button
                key={p.id}
                className={`pill ${i === idx ? 'active' : ''}`}
                onClick={() => setIdx(i)}
              >
                {String(p.sequenceNumber).padStart(2, '0')}
              </button>
            ))}
          </div>
          <button onClick={getHint} disabled={hinting}>
            {hinting ? <span className="spinner" /> : null}Request hint
          </button>
        </header>

        <div className="editor-wrap">
          <Editor
            height="100%"
            defaultLanguage="python"
            theme="vs-dark"
            value={code}
            onChange={(v) => setCode(v ?? '')}
            onMount={handleEditorMount}
            options={{
              fontSize: 13.5,
              fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
              minimap: { enabled: false },
              padding: { top: 18, bottom: 18 },
              scrollBeyondLastLine: false,
              renderLineHighlight: 'gutter',
              smoothScrolling: true,
              cursorBlinking: 'smooth',
              quickSuggestions: { other: true, comments: false, strings: false },
              suggestOnTriggerCharacters: true,
              parameterHints: { enabled: true },
              hover: { enabled: true, delay: 200 },
              tabCompletion: 'on',
            }}
          />
        </div>

        {output && (
          <div className="console">
            <div className="label">Output · exit {output.exitCode}</div>
            {output.stdout && <div className="out">{output.stdout}</div>}
            {output.stderr && <div className="err">{output.stderr}</div>}
            {!output.stdout && !output.stderr && <div>(no output)</div>}
          </div>
        )}
        {error && <div className="console"><div className="label">Error</div><div className="err">{error}</div></div>}

        <div className="actions">
          <button onClick={run} disabled={running || submitting}>
            {running ? <span className="spinner" /> : null}Run
          </button>
          <button className="primary" onClick={submit} disabled={submitting || running}>
            {submitting ? <><span className="spinner" />Grading</> : 'Submit'}
          </button>
          <div className="spacer" />
          <button onClick={next} disabled={!feedback || submitting}>
            {isLast ? 'Compile report ⟶' : 'Next problem ⟶'}
          </button>
        </div>
      </section>

      <section className="panel">
        <header className="panel-header">
          <span className="panel-title">{rightTitle}</span>
          <span className="panel-title" style={{ fontFamily: 'var(--mono)', textTransform: 'none' }}>
            {String(idx + 1).padStart(2, '0')} / {String(problems.length).padStart(2, '0')}
          </span>
        </header>
        <div className="panel-body">
          {feedback ? (
            <div className="feedback"><ReactMarkdown>{feedback}</ReactMarkdown></div>
          ) : hint ? (
            <div className="feedback"><ReactMarkdown>{hint}</ReactMarkdown></div>
          ) : (
            <div className="empty-state">
              <span className="block-hint">A quiet workbench.</span>
              Read the task in the editor, write your solution, then press
              {' '}<span className="kbd">Run</span> to execute it against Python 3.11,
              or <span className="kbd">Submit</span> to have it reviewed. Need a nudge?
              Ask for a <span className="kbd">hint</span> — it will appear here without
              giving the answer away.
            </div>
          )}
        </div>
      </section>
    </main>
  )
}
