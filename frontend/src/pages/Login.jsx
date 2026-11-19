import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { Sparkles, Loader2 } from 'lucide-react'
import { useAuth } from '../auth'

export default function Login() {
  const { user, authenticate } = useAuth()
  const navigate = useNavigate()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  if (user) return <Navigate to="/" replace />

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const submit = async (e) => {
    e.preventDefault()
    setError('')
    if (mode === 'register' && !form.name.trim()) return setError('Please enter your name.')
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(form.email)) return setError('Please enter a valid email address.')
    if (form.password.length < 8) return setError('Password must be at least 8 characters.')
    setBusy(true)
    try {
      await authenticate(mode, mode === 'login' ? { email: form.email, password: form.password } : form)
      navigate('/')
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="card w-full max-w-md p-8">
        <div className="mb-6 flex flex-col items-center text-center">
          <span className="mb-3 rounded-xl bg-indigo-600 p-2.5 text-white"><Sparkles size={22} /></span>
          <h1 className="text-2xl font-bold text-slate-900">DocuMind</h1>
          <p className="mt-1 text-sm text-slate-500">Ask questions about your own documents</p>
        </div>
        <div className="mb-5 grid grid-cols-2 rounded-xl bg-slate-100 p-1 text-sm font-medium">
          {['login', 'register'].map((m) => (
            <button key={m} type="button" onClick={() => { setMode(m); setError('') }}
              className={`rounded-lg py-2 transition ${mode === m ? 'bg-white shadow-sm text-indigo-700' : 'text-slate-500'}`}>
              {m === 'login' ? 'Sign in' : 'Register'}
            </button>
          ))}
        </div>
        <form onSubmit={submit} className="space-y-4" noValidate>
          {mode === 'register' && <input className="input" placeholder="Full name" value={form.name} onChange={set('name')} />}
          <input className="input" type="email" placeholder="Email" value={form.email} onChange={set('email')} />
          <input className="input" type="password" placeholder="Password (min 8 characters)" value={form.password} onChange={set('password')} />
          {error && <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}
          <button className="btn-primary w-full" disabled={busy}>
            {busy && <Loader2 size={16} className="animate-spin" />} {mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>
      </div>
    </div>
  )
}
