import { useState } from 'react'
import Landing from './components/Landing.jsx'
import Workspace from './components/Workspace.jsx'
import Report from './components/Report.jsx'

export default function App() {
  const [view, setView] = useState('landing')
  const [session, setSession] = useState(null)
  const [reportSubmissionId, setReportSubmissionId] = useState(null)

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">Gateway<em>.</em></span>
          <span className="tagline">Theory · Practice · Mastery</span>
        </div>
        <div className="crumbs">
          <span className={`crumb-dot ${view === 'landing' ? 'active' : ''}`} />
          <span>Material</span>
          <span className={`crumb-dot ${view === 'workspace' ? 'active' : ''}`} />
          <span>Workspace</span>
          <span className={`crumb-dot ${view === 'report' ? 'active' : ''}`} />
          <span>Report</span>
          {view !== 'landing' && (
            <button
              className="ghost"
              style={{ marginLeft: 14 }}
              onClick={() => { setView('landing'); setSession(null); setReportSubmissionId(null); }}
            >
              ← New session
            </button>
          )}
        </div>
      </header>
      {view === 'landing' && (
        <Landing onReady={(s) => { setSession(s); setView('workspace'); }} />
      )}
      {view === 'workspace' && session && (
        <Workspace
          session={session}
          onFinish={(submissionId) => { setReportSubmissionId(submissionId); setView('report'); }}
        />
      )}
      {view === 'report' && reportSubmissionId && (
        <Report submissionId={reportSubmissionId} />
      )}
    </div>
  )
}
