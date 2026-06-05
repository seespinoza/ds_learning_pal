import api from './client'

export const fetchRelationships = () => api.get('/relationships').then(r => r.data)
export const createRelationship = (data) => api.post('/relationships', data).then(r => r.data)
export const deleteRelationship = (fromLabel, fromName, type, toLabel, toName) =>
  api.delete(`/relationships/${fromLabel}/${fromName}/${type}/${toLabel}/${toName}`)
