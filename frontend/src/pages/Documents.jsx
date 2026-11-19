import { useCallback, useEffect, useRef, useState } from 'react'
import { UploadCloud, FileText, Trash2, Loader2 } from 'lucide-react'
import { api } from '../api'
import StatusBadge from '../components/StatusBadge'

export default function Documents() {
  const [docs, setDocs] = useState([])
  const [drag, setDrag] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const input = useRef()

  const load = useCallback(() => api('/documents').then(setDocs).catch((e) => setError(e.message)), [])
  useEffect(() => { load() }, [load])
  useEffect(() => {  // poll while anything is still being indexed
    if (!docs.some((d) => d.status === 'processing')) return
    const t = setInterval(load, 2000)
    return () => clearInterval(t)
  }, [docs, load])

  const upload = async (fileList) => {
    const files = [...fileList]
    if (!files.length) return
    const bad = files.find((f) => !/\.(pdf|txt)$/i.test(f.name))
    if (bad) return setError(`${bad.name}: only PDF and TXT files are supported.`)
    setError(''); setUploading(true)
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    try { await api('/documents', { method: 'POST', form }); await load() }
    catch (e) { setError(e.message) } finally { setUploading(false); input.current.value = '' }
  }
  const remove = async (d) => {
    if (!window.confirm(`Delete "${d.filename}" and its indexed chunks?`)) return
    try { await api(`/documents/${d.id}`, { method: 'DELETE' }); await load() } catch (e) { setError(e.message) }
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 md:p-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Document library</h1>
        <p className="text-slate-500">Upload PDF or TXT files. Each document is indexed independently.</p>
      </div>
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); upload(e.dataTransfer.files) }}
        onClick={() => input.current.click()}
        className={`card flex cursor-pointer flex-col items-center gap-2 border-2 border-dashed p-10 text-center transition ${drag ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 hover:border-indigo-400'}`}>
        {uploading ? <Loader2 className="animate-spin text-indigo-600" size={32} /> : <UploadCloud className="text-indigo-600" size={32} />}
        <p className="font-medium">{uploading ? 'Uploading…' : 'Drag & drop files here, or click to browse'}</p>
        <p className="text-sm text-slate-500">PDF and TXT, up to 20 MB each</p>
        <input ref={input} type="file" multiple accept=".pdf,.txt" className="hidden" onChange={(e) => upload(e.target.files)} />
      </div>
      {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
      {docs.length === 0 ? (
        <p className="text-center text-sm text-slate-500">No documents uploaded yet.</p>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {docs.map((d) => (
            <div key={d.id} className="card flex flex-col gap-3 p-5">
              <div className="flex items-start justify-between gap-2">
                <span className="rounded-xl bg-indigo-50 p-2.5 text-indigo-600"><FileText size={20} /></span>
                <button className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600" title="Delete" onClick={() => remove(d)}>
                  <Trash2 size={17} />
                </button>
              </div>
              <div className="min-w-0">
                <p className="truncate font-medium" title={d.filename}>{d.filename}</p>
                <p className="text-xs text-slate-500">{d.file_type.toUpperCase()} · {new Date(d.created_at).toLocaleDateString()}{d.status === 'indexed' && ` · ${d.chunk_count} chunks`}</p>
              </div>
              <div><StatusBadge status={d.status} /></div>
              {d.status === 'failed' && <p className="text-xs text-red-600">{d.error}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
