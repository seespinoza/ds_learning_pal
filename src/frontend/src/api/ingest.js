import api from './client'

export const triggerIngest = (inputType, inputValue) =>
  api.post('/ingest', { input_type: inputType, input_value: inputValue }).then(r => r.data)

export const confirmIngest = (proposalId, nodes, relationships) =>
  api.post('/ingest/confirm', { proposal_id: proposalId, nodes, relationships }).then(r => r.data)

export const uploadSource = (file, tags = '') => {
  const form = new FormData()
  form.append('file', file)
  form.append('tags', tags)
  return api.post('/sources', form).then(r => r.data)
}
