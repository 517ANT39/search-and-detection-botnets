import React from 'react'
import { Routes, Route } from 'react-router-dom'
import AppLayout from './components/Layout/AppLayout.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Login from './pages/Login.jsx'
import Overview from './pages/Overview.jsx'
import Topology from './pages/Topology.jsx'
import Nodes from './pages/Nodes.jsx'
import Incidents from './pages/Incidents.jsx'
import Events from './pages/Events.jsx'
import Traffic from './pages/Traffic.jsx'
import Rules from './pages/Rules.jsx'
import Reports from './pages/Reports.jsx'
import Settings from './pages/Settings.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Overview />} />
        <Route path="topology" element={<Topology />} />
        <Route path="nodes" element={<Nodes />} />
        <Route path="incidents" element={<Incidents />} />
        <Route path="events" element={<Events />} />
        <Route path="traffic" element={<Traffic />} />
        <Route path="rules" element={<Rules />} />
        <Route path="reports" element={<Reports />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}
