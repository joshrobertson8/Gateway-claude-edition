const BASE = ''

async function request(path, opts = {}) {
  const r = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json()
}

export const api = {
  createActivity: (content) =>
    request('/api/activities', { method: 'POST', body: JSON.stringify({ content }) }),
  getJob: (id) => request(`/api/jobs/${id}`),
  getProblems: (activityId) => request(`/api/activities/${activityId}/problems`),
  createSubmission: (activityId) =>
    request(`/api/activities/${activityId}/submissions`, { method: 'POST' }),
  submitResponse: (submissionId, problemId, code) =>
    request(`/api/submissions/${submissionId}/problems/${problemId}/responses`, {
      method: 'POST',
      body: JSON.stringify({ submittedCode: code }),
    }),
  getResponse: (submissionId, problemId) =>
    request(`/api/submissions/${submissionId}/problems/${problemId}/responses`),
  startReport: (submissionId) =>
    request(`/api/submissions/${submissionId}/report`, { method: 'POST' }),
  getReport: (submissionId) => request(`/api/submissions/${submissionId}/report`),
  runCode: (code) =>
    request('/api/run', { method: 'POST', body: JSON.stringify({ code }) }),
  hint: (problemText, code) =>
    request('/api/hint', {
      method: 'POST',
      body: JSON.stringify({ problemText, code }),
    }),
}

export async function pollJob(jobId, { intervalMs = 2000, timeoutMs = 1800000 } = {}) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    const job = await api.getJob(jobId)
    if (job.status === 'completed') return job
    if (job.status === 'failed') throw new Error(job.errorMessage || 'job failed')
    await new Promise((r) => setTimeout(r, intervalMs))
  }
  throw new Error('job timed out')
}
