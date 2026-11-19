import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Send, Plus, Loader2, FileText, Bot, User as UserIcon, MessageSquare } from 'lucide-react'
import { api } from '../api'

function Sources({ sources }) {
  if (!sources?.length) return null
  return (
    <div className="mt-3 grid gap-2 sm:grid-cols-2">
      {sources.map((s, i) => (
        <div key={i} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-700">
            <span className="flex h-5 w-5 items-center justify-center rounded-full bg-indigo-100">{i + 1}</span>
            <FileText size={13} /> <span className="truncate">{s.filename}</span>
            <span className="ml-auto shrink-0 rounded-md bg-white px-1.5 py-0.5 text-slate-600">p. {s.page}</span>
          </div>
          <p className="mt-2 line-clamp-3 text-xs text-slate-600">{s.snippet}</p>
        </div>
      ))}
    </div>
  )
}

export default function Chat() {
  const [convs, setConvs] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [messages, setMessages] = useState([])
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [docCount, setDocCount] = useState(null)
  const bottom = useRef()

  const loadConvs = () => api('/conversations').then(setConvs).catch(() => {})
  useEffect(() => { loadConvs(); api('/documents').then((d) => setDocCount(d.length)).catch(() => {}) }, [])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  const open = async (id) => {
    setError(''); setActiveId(id)
    try { setMessages((await api(`/conversations/${id}`)).messages) } catch (e) { setError(e.message) }
  }
  const newChat = () => { setActiveId(null); setMessages([]); setError('') }

  const send = async (e) => {
    e.preventDefault()
    const q = text.trim()
    if (!q || busy) return
    setText(''); setError(''); setBusy(true)
    setMessages((m) => [...m, { role: 'user', content: q }])
    try {
      const r = await api('/chat', { method: 'POST', body: { query: q, conversation_id: activeId } })
      setActiveId(r.conversation_id)
      setMessages((m) => [...m, { role: 'assistant', content: r.answer, sources: r.sources }])
      loadConvs()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <div className="flex h-full">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-white p-3 lg:flex">
        <button className="btn-primary mb-3 w-full" onClick={newChat}><Plus size={16} /> New chat</button>
        <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">History</p>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {convs.length === 0 && <p className="px-2 text-sm text-slate-400">No conversations yet.</p>}
          {convs.map((c) => (
            <button key={c.id} onClick={() => open(c.id)}
              className={`flex w-full items-center gap-2 rounded-xl px-3 py-2 text-left text-sm transition ${activeId === c.id ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'}`}>
              <MessageSquare size={15} className="shrink-0" /><span className="truncate">{c.title}</span>
            </button>
          ))}
        </div>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-slate-200 bg-white p-2 lg:hidden">
          <button className="btn-ghost" onClick={newChat}><Plus size={16} /> New</button>
          <select className="input !py-1.5" value={activeId ?? ''} onChange={(e) => e.target.value ? open(Number(e.target.value)) : newChat()}>
            <option value="">Current chat</option>
            {convs.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
          </select>
        </div>
        <div className="flex-1 space-y-5 overflow-y-auto p-4 md:p-8">
          {messages.length === 0 && (
            <div className="mx-auto mt-16 max-w-md text-center text-slate-500">
              <Bot className="mx-auto mb-3 text-indigo-500" size={36} />
              <p className="font-medium text-slate-700">Ask anything about your documents</p>
              {docCount === 0
                ? <p className="mt-1 text-sm">You have no documents yet — <Link className="text-indigo-600" to="/documents">upload one first</Link>.</p>
                : <p className="mt-1 text-sm">Answers include the source file and page number.</p>}
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
              <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${m.role === 'user' ? 'bg-slate-200 text-slate-600' : 'bg-indigo-600 text-white'}`}>
                {m.role === 'user' ? <UserIcon size={16} /> : <Bot size={16} />}
              </span>
              <div className={`max-w-[85%] ${m.role === 'user' ? 'rounded-2xl rounded-tr-sm bg-indigo-600 px-4 py-2.5 text-white' : 'card rounded-tl-sm px-4 py-3'}`}>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{m.content}</p>
                {m.role === 'assistant' && <Sources sources={m.sources} />}
              </div>
            </div>
          ))}
          {busy && (
            <div className="flex items-center gap-3 text-sm text-slate-500">
              <span className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-white"><Bot size={16} /></span>
              <Loader2 size={16} className="animate-spin" /> Searching your documents…
            </div>
          )}
          {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
          <div ref={bottom} />
        </div>
        <form onSubmit={send} className="border-t border-slate-200 bg-white p-3 md:p-4">
          <div className="mx-auto flex max-w-3xl gap-2">
            <input className="input" placeholder="Ask a question about your documents…" value={text} onChange={(e) => setText(e.target.value)} disabled={busy} />
            <button className="btn-primary" disabled={busy || !text.trim()}><Send size={16} /></button>
          </div>
        </form>
      </section>
    </div>
  )
}
