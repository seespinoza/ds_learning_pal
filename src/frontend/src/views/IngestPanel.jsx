import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { triggerIngest, confirmIngest, uploadSource } from '../api/ingest'

const CONFIDENCE_OPTS = ['high', 'medium', 'low']

export default function IngestPanel() {
  const [inputType, setInputType] = useState('text')
  const [inputValue, setInputValue] = useState('')
  const [file, setFile] = useState(null)
  const [proposal, setProposal] = useState(null)
  const [editedNodes, setEditedNodes] = useState([])
  const [editedRels, setEditedRels] = useState([])
  const qc = useQueryClient()

  const ingestMut = useMutation({
    mutationFn: async () => {
      let value = inputValue
      if (inputType === 'pdf' && file) {
        const uploaded = await uploadSource(file)
        value = file.name
      }
      return triggerIngest(inputType, value)
    },
    onSuccess: (data) => {
      setProposal(data)
      setEditedNodes(data.nodes?.map(n => ({ ...n, _keep: true })) ?? [])
      setEditedRels(data.relationships?.map(r => ({ ...r, _keep: true })) ?? [])
    },
  })

  const confirmMut = useMutation({
    mutationFn: () => confirmIngest(
      proposal.proposal_id,
      editedNodes.filter(n => n._keep).map(({ _keep, ...n }) => n),
      editedRels.filter(r => r._keep).map(({ _keep, ...r }) => r),
    ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['nodes'] })
      qc.invalidateQueries({ queryKey: ['relationships'] })
      setProposal(null)
      setInputValue('')
      setFile(null)
    },
  })

  return (
    <div className="max-w-3xl mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold text-white">Ingest</h1>

      {!proposal && (
        <div className="bg-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex gap-2">
            {['text', 'url', 'pdf'].map(t => (
              <button
                key={t}
                onClick={() => setInputType(t)}
                className={`px-3 py-1.5 rounded text-sm ${inputType === t ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
              >
                {t.toUpperCase()}
              </button>
            ))}
          </div>

          {inputType === 'pdf' ? (
            <input
              type="file"
              accept=".pdf"
              onChange={e => setFile(e.target.files[0])}
              className="block w-full text-sm text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-indigo-600 file:text-white"
            />
          ) : (
            <textarea
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              placeholder={inputType === 'url' ? 'https://…' : 'Paste text or notes here…'}
              rows={6}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white resize-none placeholder-slate-500"
            />
          )}

          <button
            onClick={() => ingestMut.mutate()}
            disabled={ingestMut.isPending || (!inputValue && !file)}
            className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium"
          >
            {ingestMut.isPending ? 'Analyzing…' : 'Run Ingest'}
          </button>

          {ingestMut.isError && (
            <p className="text-red-400 text-sm">{ingestMut.error?.message}</p>
          )}
        </div>
      )}

      {proposal && (
        <div className="space-y-6">
          <div className="bg-slate-800 rounded-xl p-5 space-y-3">
            <h2 className="text-lg font-medium text-white">Proposed Nodes ({editedNodes.length})</h2>
            <div className="space-y-2">
              {editedNodes.map((node, i) => (
                <div key={i} className={`flex items-start gap-3 p-3 rounded-lg ${node._keep ? 'bg-slate-700' : 'bg-slate-800 opacity-50'}`}>
                  <input
                    type="checkbox"
                    checked={node._keep}
                    onChange={e => {
                      const copy = [...editedNodes]
                      copy[i]._keep = e.target.checked
                      setEditedNodes(copy)
                    }}
                    className="mt-1"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-indigo-400 font-mono">{node.label}</span>
                      <span className="text-white font-medium text-sm">{node.name}</span>
                    </div>
                    {node.summary && (
                      <p className="text-slate-400 text-xs mt-0.5 leading-relaxed">{node.summary}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-slate-800 rounded-xl p-5 space-y-3">
            <h2 className="text-lg font-medium text-white">Proposed Relationships ({editedRels.length})</h2>
            <div className="space-y-2">
              {editedRels.map((rel, i) => (
                <div key={i} className={`flex items-center gap-3 p-3 rounded-lg ${rel._keep ? 'bg-slate-700' : 'bg-slate-800 opacity-50'}`}>
                  <input
                    type="checkbox"
                    checked={rel._keep}
                    onChange={e => {
                      const copy = [...editedRels]
                      copy[i]._keep = e.target.checked
                      setEditedRels(copy)
                    }}
                  />
                  <div className="flex-1 text-sm">
                    <span className="text-white">{rel.from}</span>
                    <span className="mx-2 text-indigo-400 font-mono text-xs">—[{rel.type}]→</span>
                    <span className="text-white">{rel.to}</span>
                  </div>
                  <select
                    value={rel.confidence}
                    onChange={e => {
                      const copy = [...editedRels]
                      copy[i].confidence = e.target.value
                      setEditedRels(copy)
                    }}
                    className="bg-slate-600 text-xs text-slate-300 rounded px-1 py-0.5 border border-slate-500"
                  >
                    {CONFIDENCE_OPTS.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => confirmMut.mutate()}
              disabled={confirmMut.isPending}
              className="flex-1 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium"
            >
              {confirmMut.isPending ? 'Committing…' : `Confirm (${editedNodes.filter(n => n._keep).length} nodes, ${editedRels.filter(r => r._keep).length} rels)`}
            </button>
            <button
              onClick={() => setProposal(null)}
              className="px-6 py-2.5 rounded-lg bg-slate-700 hover:bg-slate-600 text-white"
            >
              Discard
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
