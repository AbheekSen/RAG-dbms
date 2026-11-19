import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { FileText, MessageSquare, ArrowRight } from 'lucide-react'
import { api } from '../api'
import { useAuth } from '../auth'
import StatusBadge from '../components/StatusBadge'

export default function Dashboard() {
  const { user } = useAuth()
  const [docs, setDocs] = useState([])
  const [convs, setConvs] = useState([])
  useEffect(() => {
    api('/documents').then(setDocs).catch(() => {})
    api('/conversations').then(setConvs).catch(() => {})
  }, [])

  const stat = (icon, label, value, to) => (
    <Link to={to} className="card flex items-center gap-4 p-5 transition hover:border-indigo-300">
      <span className="rounded-xl bg-indigo-50 p-3 text-indigo-600">{icon}</span>
      <div><div className="text-2xl font-bold">{value}</div><div className="text-sm text-slate-500">{label}</div></div>
    </Link>
  )
  return (
    <div className="mx-auto max-w-5xl space-y-6 p-4 md:p-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Welcome back, {user.name.split(' ')[0]}</h1>
        <p className="text-slate-500">Upload documents and ask questions with cited answers.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {stat(<FileText size={22} />, 'Documents', docs.length, '/documents')}
        {stat(<MessageSquare size={22} />, 'Conversations', convs.length, '/chat')}
      </div>
      <div className="card">
        <div className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
          <h2 className="font-semibold">Recent documents</h2>
          <Link to="/documents" className="flex items-center gap-1 text-sm font-medium text-indigo-600">Manage <ArrowRight size={14} /></Link>
        </div>
        {docs.length === 0 ? (
          <p className="p-6 text-sm text-slate-500">No documents yet. <Link className="text-indigo-600" to="/documents">Upload your first one.</Link></p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {docs.slice(0, 5).map((d) => (
              <li key={d.id} className="flex items-center justify-between px-5 py-3">
                <div className="flex items-center gap-3"><FileText size={18} className="text-slate-400" /><span className="text-sm font-medium">{d.filename}</span></div>
                <StatusBadge status={d.status} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
