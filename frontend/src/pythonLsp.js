// Python IDE bridge: Pyodide + jedi (completions/hover/signatures) + pyflakes (diagnostics).
// Loads Pyodide once from CDN on first editor mount. Subsequent editors reuse it.

const PYODIDE_VERSION = 'v0.26.4'
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/${PYODIDE_VERSION}/full/`

let pyodidePromise = null

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = src
    s.onload = resolve
    s.onerror = () => reject(new Error(`failed to load ${src}`))
    document.head.appendChild(s)
  })
}

async function getPyodide() {
  if (pyodidePromise) return pyodidePromise
  pyodidePromise = (async () => {
    if (!window.loadPyodide) await loadScript(`${PYODIDE_URL}pyodide.js`)
    const pyodide = await window.loadPyodide({ indexURL: PYODIDE_URL })
    await pyodide.loadPackage('micropip')
    await pyodide.runPythonAsync(`
import micropip
await micropip.install(['jedi', 'pyflakes'])

import io, jedi
import pyflakes.api, pyflakes.reporter

def lint(source):
    out, err = io.StringIO(), io.StringIO()
    reporter = pyflakes.reporter.Reporter(out, err)
    try:
        pyflakes.api.check(source, '<code>', reporter)
    except Exception:
        pass
    msgs = []
    for line in (out.getvalue() + err.getvalue()).splitlines():
        if '<code>:' not in line:
            continue
        rest = line.split('<code>:', 1)[1]
        parts = rest.split(':', 2)
        try:
            if len(parts) == 3:
                ln, col, msg = int(parts[0]), int(parts[1]), parts[2].strip()
            else:
                ln, col, msg = int(parts[0]), 1, parts[1].strip()
            msgs.append((ln, col, msg))
        except Exception:
            continue
    return msgs

def complete(source, line, col):
    try:
        script = jedi.Script(code=source)
        cs = script.complete(line, col)
    except Exception:
        return []
    out = []
    for c in cs[:60]:
        try:
            doc = c.docstring(raw=True) or ''
        except Exception:
            doc = ''
        out.append({
            'label': c.name,
            'kind': c.type or 'text',
            'detail': (c.description or '')[:120],
            'doc': doc[:1200],
            'insert': c.complete or c.name,
        })
    return out

def hover_info(source, line, col):
    try:
        script = jedi.Script(code=source)
        helps = script.help(line, col)
    except Exception:
        return None
    if not helps:
        return None
    h = helps[0]
    try:
        doc = h.docstring() or ''
    except Exception:
        doc = ''
    return {'name': h.name or '', 'description': h.description or '', 'doc': doc[:2000]}

def signatures(source, line, col):
    try:
        script = jedi.Script(code=source)
        sigs = script.get_signatures(line, col)
    except Exception:
        return None
    if not sigs:
        return None
    s = sigs[0]
    return {
        'label': s.to_string(),
        'params': [p.to_string() for p in s.params],
        'active': s.index if s.index is not None else 0,
    }
`)
    return pyodide
  })()
  return pyodidePromise
}

const KIND_MAP = {
  module: 'Module',
  class: 'Class',
  instance: 'Variable',
  function: 'Function',
  method: 'Method',
  param: 'Variable',
  keyword: 'Keyword',
  property: 'Property',
  statement: 'Variable',
  path: 'File',
}

let providersRegistered = false

function toJs(proxy) {
  try {
    return proxy.toJs({ dict_converter: Object.fromEntries })
  } finally {
    if (proxy && typeof proxy.destroy === 'function') proxy.destroy()
  }
}

export async function initPythonLsp(monaco) {
  const pyodide = await getPyodide()

  if (!providersRegistered) {
    providersRegistered = true

    monaco.languages.registerCompletionItemProvider('python', {
      triggerCharacters: ['.', '(', ',', ' '],
      provideCompletionItems(model, position) {
        const src = model.getValue()
        const complete = pyodide.globals.get('complete')
        let res
        try {
          res = toJs(complete(src, position.lineNumber, position.column - 1))
        } catch (e) {
          return { suggestions: [] }
        } finally {
          complete.destroy()
        }
        const word = model.getWordUntilPosition(position)
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn,
        }
        const kinds = monaco.languages.CompletionItemKind
        return {
          suggestions: (res || []).map((c) => ({
            label: c.label,
            kind: kinds[KIND_MAP[c.kind] || 'Text'] ?? kinds.Text,
            detail: c.detail,
            documentation: c.doc ? { value: c.doc } : undefined,
            insertText: c.label,
            range,
          })),
        }
      },
    })

    monaco.languages.registerHoverProvider('python', {
      provideHover(model, position) {
        const src = model.getValue()
        const hoverFn = pyodide.globals.get('hover_info')
        let r
        try {
          const proxy = hoverFn(src, position.lineNumber, position.column)
          if (!proxy) return null
          r = toJs(proxy)
        } catch {
          return null
        } finally {
          hoverFn.destroy()
        }
        if (!r) return null
        const contents = []
        if (r.description) contents.push({ value: '```python\n' + r.description + '\n```' })
        if (r.doc) contents.push({ value: r.doc })
        return { contents }
      },
    })

    monaco.languages.registerSignatureHelpProvider('python', {
      signatureHelpTriggerCharacters: ['(', ','],
      provideSignatureHelp(model, position) {
        const src = model.getValue()
        const sigFn = pyodide.globals.get('signatures')
        let r
        try {
          const proxy = sigFn(src, position.lineNumber, position.column)
          if (!proxy) return null
          r = toJs(proxy)
        } catch {
          return null
        } finally {
          sigFn.destroy()
        }
        if (!r) return null
        return {
          value: {
            signatures: [
              {
                label: r.label,
                parameters: (r.params || []).map((p) => ({ label: p })),
              },
            ],
            activeSignature: 0,
            activeParameter: r.active || 0,
          },
          dispose: () => {},
        }
      },
    })
  }

  return {
    lint(model) {
      if (!model) return
      const src = model.getValue()
      const lintFn = pyodide.globals.get('lint')
      let rows
      try {
        rows = toJs(lintFn(src))
      } catch {
        rows = []
      } finally {
        lintFn.destroy()
      }
      const markers = (rows || []).map(([line, col, msg]) => ({
        severity: monaco.MarkerSeverity.Error,
        startLineNumber: line,
        startColumn: col,
        endLineNumber: line,
        endColumn: col + 1,
        message: msg,
        source: 'pyflakes',
      }))
      monaco.editor.setModelMarkers(model, 'pyflakes', markers)
    },
  }
}
