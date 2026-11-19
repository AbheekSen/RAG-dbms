import { useEffect, useState } from 'react'
import { Users, FileText, Layers, MessageSquare, Mail } from 'lucide-react'
import { api } from '../api'
import StatusBadge from '../components/StatusBadge'

export default function Admin() {
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [docs, setDocs] = useState([])
  const [error, setError] = useState('')
  useEffect(() => {
    Promise.all([api('/admin/stats'), api('/admin/users'), api('/admin/documents')])
      .then(([s, u, d]) => { setStats(s); setUsers(u); setDocs(d) })
      .catch((e) => setError(e.message))
  }, [])

  const cards = stats && [
    ['Users', stats.users, Users], ['Documents', stats.documents, FileText],
    ['Chunks', stats.chunks, Layers], ['Conversations', stats.conversations, MessageSquare],
    ['Messages', stats.messages, Mail],
  ]
  const th = 'px-5 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500'
  const td = 'px-5 py-3 text-sm'
  return (
    <div className="mx-auto max-w-6xl space-y-6 p-4 md:p-8">
      <h1 className="text-2xl font-bold text-slate-900">Admin dashboard</h1>
      {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {cards?.map(([label, value, Icon]) => (
          <div key={label} className="card flex items-center gap-3 p-4">
            <span className="rounded-xl bg-indigo-50 p-2.5 text-indigo-600"><Icon size={18} /></span>
            <div><div className="text-xl font-bold">{value}</div><div className="text-xs text-slate-500">{label}</div></div>
          </div>
        ))}
      </div>
      <div className="card overflow-x-auto">
        <h2 className="border-b border-slate-100 px-5 py-4 font-semibold">Registered users</h2>
        <table className="w-full"><thead className="bg-slate-50"><tr>
          {['Name', 'Email', 'Role', 'Documents', 'Conversations', 'Joined'].map((h) => <th key={h} className={th}>{h}</th>)}
        </tr></thead><tbody className="divide-y divide-slate-100">
          {users.map((u) => (
            <tr key={u.id}><td className={td}>{u.name}</td><td className={td}>{u.email}</td>
              <td className={td}><span className={`rounded-full px-2.5 py-1 text-xs font-medium ${u.role === 'admin' ? 'bg-indigo-50 text-indigo-700' : 'bg-slate-100 text-slate-600'}`}>{u.role}</span></td>
              <td className={td}>{u.documents}</td><td className={td}>{u.conversations}</td>
              <td className={td}>{new Date(u.created_at).toLocaleDateString()}</td></tr>
          ))}
        </tbody></table>
      </div>
      <div className="card overflow-x-auto">
        <h2 className="border-b border-slate-100 px-5 py-4 font-semibold">All documents</h2>
        <table className="w-full"><thead className="bg-slate-50"><tr>
          {['Filename', 'Owner', 'Type', 'Chunks', 'Status', 'Uploaded'].map((h) => <th key={h} className={th}>{h}</th>)}
        </tr></thead><tbody className="divide-y divide-slate-100">
          {docs.map((d) => (
            <tr key={d.id}><td className={td}>{d.filename}</td><td className={td}>{d.owner_email}</td>
              <td className={td}>{d.file_type.toUpperCase()}</td><td className={td}>{d.chunk_count}</td>
              <td className={td}><StatusBadge status={d.status} /></td>
              <td className={td}>{new Date(d.created_at).toLocaleDateString()}</td></tr>
          ))}
          {docs.length === 0 && <tr><td className={td} colSpan={6}>No documents uploaded yet.</td></tr>}
        </tbody></table>
      </div>
    </div>
  )
}
