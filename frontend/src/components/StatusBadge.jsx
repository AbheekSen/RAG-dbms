import { CheckCircle2, Loader2, XCircle } from 'lucide-react'

export default function StatusBadge({ status }) {
  const map = {
    indexed: ['bg-emerald-50 text-emerald-700', <CheckCircle2 size={13} />, 'Indexed'],
    processing: ['bg-amber-50 text-amber-700', <Loader2 size={13} className="animate-spin" />, 'Indexing'],
    failed: ['bg-red-50 text-red-700', <XCircle size={13} />, 'Failed'],
  }
  const [cls, icon, label] = map[status] || map.failed
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ${cls}`}>{icon}{label}</span>
}
