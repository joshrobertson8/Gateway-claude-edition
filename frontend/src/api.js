const BASE = import.meta.env.VITE_API_BASE ?? '/_/backend'

async function request(path, opts = {}) {
  const r = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}

export const api = {
  // Returns { activityId, problems: [{id, sequenceNumber, problemText}] }
  createActivity: (content) =>
    request('/api/activities', { method: 'POST', body: JSON.stringify({ content }) }),
  getProblems: (activityId) => request(`/api/activities/${activityId}/problems`),
  createSubmission: (activityId) =>
    request(`/api/activities/${activityId}/submissions`, { method: 'POST' }),
  // Returns { problemResponseId, aiFeedback }
  submitResponse: (submissionId, problemId, code) =>
    request(`/api/submissions/${submissionId}/problems/${problemId}/responses`, {
      method: 'POST',
      body: JSON.stringify({ submittedCode: code }),
    }),
  getResponse: (submissionId, problemId) =>
    request(`/api/submissions/${submissionId}/problems/${problemId}/responses`),
  // Returns { submissionId, feedbackReport }
  generateReport: (submissionId) =>
    request(`/api/submissions/${submissionId}/report`, { method: 'POST' }),
  getReport: (submissionId) => request(`/api/submissions/${submissionId}/report`),
  hint: (problemText, code) =>
    request('/api/hint', {
      method: 'POST',
      body: JSON.stringify({ problemText, code }),
    }),
}
