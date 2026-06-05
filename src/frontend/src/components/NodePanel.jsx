import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { updateNode, deleteNode } from '../api/nodes'

const ARRAY_FIELDS = ['aliases', 'raw_sources', 'courses', 'videos', 'docs', 'references']

export default function NodePanel({ node, onClose }) {
  const [editing, setEditing] = useState(false)
  const qc = useQueryClient()
  const { register, handleSubmit } = useForm({ defaultValues: node })

  const updateMut = useMutation({
    mutationFn: ({ label, name, ...rest }) => updateNode(label, name, rest),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['nodes'] }); setEditing(false) },
  })

  const deleteMut = useMutation({
    mutationFn: () => deleteNode(node.label, node.name),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['nodes'] }); onClose() },
  })

  const onSubmit = (data) => {
    const clean = {}
    for (const [k, v] of Object.entries(data)) {
      if (ARRAY_FIELDS.includes(k)) {
        clean[k] = typeof v === 'string' ? v.split(',').map(s => s.trim()).filter(Boolean) : v
      } else {
        clean[k] = v
      }
    }
    updateMut.mutate({ label: node.label, name: node.name, ...clean })
  }

  return (
    <div className="absolute right-0 top-0 h-full w-80 bg-slate-900 border-l border-slate-700 overflow-y-auto p-4 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <span className="text-xs font-mono text-indigo-400 uppercase">{node.label}</span>
          <h2 className="text-lg font-semibold text-white">{node.name}</h2>
        </div>
        <button onClick={onClose} className="text-slate-400 hover:text-white text-xl leading-none">×</button>
      </div>

      {!editing ? (
        <div className="space-y-3 text-sm text-slate-300">
          {node.summary && <p className="leading-relaxed">{node.summary}</p>}

          {ARRAY_FIELDS.map(field => {
            const val = node[field]
            if (!val || val.length === 0) return null
            return (
              <div key={field}>
                <span className="text-slate-500 text-xs uppercase">{field}</span>
                <ul className="mt-1 space-y-0.5">
                  {val.map((v, i) => <li key={i} className="text-xs">{v}</li>)}
                </ul>
              </div>
            )
          })}

          {node.notes && (
            <div>
              <span className="text-slate-500 text-xs uppercase">Notes</span>
              <p className="mt-1 text-xs">{node.notes}</p>
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <button
              onClick={() => setEditing(true)}
              className="flex-1 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs"
            >
              Edit
            </button>
            <button
              onClick={() => { if (confirm(`Delete ${node.name}?`)) deleteMut.mutate() }}
              className="flex-1 py-1.5 rounded bg-slate-700 hover:bg-red-700 text-white text-xs"
            >
              Delete
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-3 text-sm">
          <div>
            <label className="text-slate-400 text-xs block mb-1">Summary</label>
            <textarea
              {...register('summary')}
              rows={3}
              className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-white resize-none"
            />
          </div>

          {ARRAY_FIELDS.map(field => (
            <div key={field}>
              <label className="text-slate-400 text-xs block mb-1">{field} (comma-separated)</label>
              <input
                {...register(field, {
                  setValueAs: v => Array.isArray(v) ? v.join(', ') : v
                })}
                className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-white"
              />
            </div>
          ))}

          <div>
            <label className="text-slate-400 text-xs block mb-1">Notes</label>
            <textarea
              {...register('notes')}
              rows={2}
              className="w-full bg-slate-800 border border-slate-600 rounded px-2 py-1 text-xs text-white resize-none"
            />
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={updateMut.isPending}
              className="flex-1 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-xs"
            >
              {updateMut.isPending ? 'Saving…' : 'Save'}
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="flex-1 py-1.5 rounded bg-slate-700 hover:bg-slate-600 text-white text-xs"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  )
}
