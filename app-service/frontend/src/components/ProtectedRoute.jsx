import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()
  if (loading) return <div className="h-screen flex items-center justify-center text-muted">Загрузка...</div>
  if (!isAuthenticated) return <Navigate to="/login" state={{ from: location }} replace />
  return children
}
