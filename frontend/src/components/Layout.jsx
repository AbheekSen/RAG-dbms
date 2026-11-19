import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { LayoutDashboard, FileText, MessageSquare, ShieldCheck, LogOut, Menu, X, Sparkles } from 'lucide-react'
import { useAuth } from '../auth'

export default function Layout() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()
  const items = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
    { to: '/documents', label: 'Documents', icon: FileText },
    { to: '/chat', label: 'AI Chat', icon: MessageSquare },
    ...(user.role === 'admin' ? [{ to: '/admin', label: 'Admin', icon: ShieldCheck }] : []),
  ]
  const link = ({ isActive }) =>
    `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
      isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100'}`

  return (
    <div className="flex h-screen overflow-hidden">
      {open && <div className="fixed inset-0 z-20 bg-slate-900/30 md:hidden" onClick={() => setOpen(false)} />}
      <aside className={`fixed z-30 flex h-full w-64 flex-col border-r border-slate-200 bg-white p-4 transition-transform md:static md:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="mb-6 flex items-center justify-between px-2">
          <div className="flex items-center gap-2 text-lg font-bold text-slate-900">
            <span className="rounded-lg bg-indigo-600 p-1.5 text-white"><Sparkles size={18} /></span> DocuMind
          </div>
          <button className="md:hidden" onClick={() => setOpen(false)}><X size={20} /></button>
        </div>
        <nav className="flex flex-1 flex-col gap-1">
          {items.map(({ to, label, icon: Icon, end }) => (
            <NavLink key={to} to={to} end={end} className={link} onClick={() => setOpen(false)}>
              <Icon size={18} /> {label}
            </NavLink>
          ))}
        </nav>
        <p className="px-2 text-xs text-slate-400">Answers grounded in your own documents.</p>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-8">
          <button className="md:hidden" onClick={() => setOpen(true)}><Menu size={22} /></button>
          <div className="hidden md:block" />
          <div className="flex items-center gap-3">
            <div className="text-right">
              <div className="text-sm font-medium leading-tight">{user.name}</div>
              <div className="text-xs text-slate-500">{user.role === 'admin' ? 'Admin' : 'Standard user'}</div>
            </div>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-indigo-100 text-sm font-semibold text-indigo-700">
              {user.name[0].toUpperCase()}
            </div>
            <button className="btn-ghost !px-2.5" title="Log out" onClick={() => { logout(); navigate('/login') }}>
              <LogOut size={18} />
            </button>
          </div>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto"><Outlet /></main>
      </div>
    </div>
  )
}
