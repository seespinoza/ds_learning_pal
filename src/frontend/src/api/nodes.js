import api from './client'

export const fetchNodes = () => api.get('/nodes').then(r => r.data)
export const fetchNode = (label, name) => api.get(`/nodes/${label}/${name}`).then(r => r.data)
export const createNode = (data) => api.post('/nodes', data).then(r => r.data)
export const updateNode = (label, name, data) => api.patch(`/nodes/${label}/${name}`, data).then(r => r.data)
export const deleteNode = (label, name) => api.delete(`/nodes/${label}/${name}`)
