import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { api } from '../api.js'

export default function Report({ submissionId }) {
  const [report, setReport] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getReport(submissionId).then((r) => {
      setReport(r.feedbackReport || '(no report yet)')
      setLoading(false)
    })
  }, [submissionId])

  return (
    <main className="report-wrap">
      <article className="report-card fade-up">
        <div className="report-eyebrow">Session Dossier · #{submissionId}</div>
        <h1 className="report-title">
          A record of <em>today&apos;s</em> work.
        </h1>
        <p className="report-sub">
          Strengths, opportunities, and a few next steps — synthesised from every
          problem in this session.
        </p>
        {loading ? (
          <div className="empty-state"><span className="spinner" />Loading…</div>
        ) : (
          <div className="feedback"><ReactMarkdown>{report}</ReactMarkdown></div>
        )}
      </article>
    </main>
  )
}
