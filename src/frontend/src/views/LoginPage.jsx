import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { login } from '../api/auth'

export default function LoginPage({ onLogin }) {
  const { register, handleSubmit } = useForm()
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const onSubmit = async (data) => {
    setLoading(true)
    setError('')
    try {
      const res = await login(data.username, data.password)
      localStorage.setItem('token', res.access_token)
      onLogin(res.access_token)
    } catch (e) {
      setError(e.response?.data?.detail ?? 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="bg-slate-800 rounded-2xl p-8 w-80 space-y-5 shadow-xl">
        <div className="text-center">
          <h1 className="text-xl font-semibold text-white">DS Learning Pal</h1>
          <p className="text-slate-400 text-sm mt-1">Sign in to continue</p>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="text-slate-400 text-xs block mb-1">Username</label>
            <input
              {...register('username', { required: true })}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
          <div>
            <label className="text-slate-400 text-xs block mb-1">Password</label>
            <input
              type="password"
              {...register('password', { required: true })}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white"
            />
          </div>
          {error && <p className="text-red-400 text-xs">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium"
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  )
}
