import { useState } from 'react'
import { api, pollJob } from '../api.js'

export default function Landing({ onReady }) {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [drag, setDrag] = useState(false)

  async function handleFiles(files) {
    const file = files[0]
    if (!file) return
    const t = await file.text()
    setText(t)
  }

  async function start() {
    setError('')
    if (!text.trim()) { setError('Paste or drop some learning material first.'); return }
    setLoading(true)
    try {
      setStatus('Creating activity…')
      const { activityId, jobId } = await api.createActivity(text)
      setStatus('Generating challenges…')
      await pollJob(jobId)
      setStatus('Loading workspace…')
      const { problems } = await api.getProblems(activityId)
      const { submissionId } = await api.createSubmission(activityId)
      onReady({ activityId, submissionId, problems })
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  return (
    <main className="landing">
      <section className="landing-hero">
        <div className="eyebrow fade-up">Gateway · No. 001</div>
        <h1 className="display fade-up d1">
          From theory,<br />
          to <em>practice.</em>
        </h1>
        <p className="lede fade-up d2">
          Drop in a reading, a slide deck, or documentation. Gateway synthesises
          a bespoke set of Python challenges you can solve, run, and have graded
          — without leaving the page.
        </p>
        <dl className="hero-meta fade-up d3">
          <div>
            <dt>Engine</dt>
            <dd>gpt-oss · local</dd>
          </div>
          <div>
            <dt>Runtime</dt>
            <dd>Python 3.11</dd>
          </div>
          <div>
            <dt>Session</dt>
            <dd>Ephemeral</dd>
          </div>
        </dl>
      </section>

      <section className="landing-form">
        <div className="fade-up d2">
          <div className="form-label">01 · Source material</div>
          <div
            className={`dropzone ${drag ? 'drag' : ''}`}
            onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault(); setDrag(false)
              handleFiles(e.dataTransfer.files)
            }}
            onClick={() => document.getElementById('fileinput').click()}
          >
            <span className="mark">⁂</span>
            <div>Drop a .txt or .md file, or click to browse</div>
            <div className="hint">Plain text · Markdown</div>
            <input
              id="fileinput"
              type="file"
              accept=".txt,.md,.text"
              style={{ display: 'none' }}
              onChange={(e) => handleFiles(e.target.files)}
            />
          </div>
        </div>

        <div className="divider-or fade-up d3"><span>or paste below</span></div>

        <div className="fade-up d3">
          <textarea
            className="material"
            placeholder="Paste readings, lecture notes, or documentation…"
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="cta-row fade-up d4">
          <span className="status">
            {loading ? <><span className="spinner" />{status}</> : 'Ready when you are.'}
          </span>
          <button className="primary" onClick={start} disabled={loading}>
            Generate challenges ⟶
          </button>
        </div>
      </section>
    </main>
  )
}
