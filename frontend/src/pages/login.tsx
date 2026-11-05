import { useState, type FormEvent } from 'react'
import { api } from '../api'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

export default function Login(){
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const nav = useNavigate()

  async function submit(e: FormEvent<HTMLFormElement>){
    e.preventDefault()
    setError('')
    setLoading(true)
    try{
      const {data} = await api.post('/auth/login', {username, password})
      localStorage.setItem('vita_token', data.access_token)
      localStorage.setItem('vita_user', JSON.stringify(data.user))
      nav('/')
    }catch(error: unknown){
      const detail = axios.isAxiosError<{ detail?: string }>(error) ? error.response?.data?.detail : undefined
      setError(detail || 'Connexion impossible. Vérifiez vos identifiants et réessayez.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <form onSubmit={submit} className="login-card">
        <div className="login-brand"><span className="brand-mark">V</span><span><strong>VITA</strong><small>ESPACE DE PILOTAGE</small></span></div>
        <div><h1>Bon retour</h1><p>Connectez-vous à votre espace de travail.</p></div>
        {error && <p role="alert" className="login-error">{error}</p>}
        <label className="field"><span>Identifiant</span><input autoComplete="username" required value={username} onChange={e=>setUsername(e.target.value)} placeholder="Votre identifiant" /></label>
        <label className="field"><span>Mot de passe</span><input autoComplete="current-password" required type="password" value={password} onChange={e=>setPassword(e.target.value)} placeholder="Votre mot de passe" /></label>
        <button disabled={loading} className="login-submit">{loading ? 'Connexion…' : 'Se connecter'}</button>
      </form>
    </div>
  )
}