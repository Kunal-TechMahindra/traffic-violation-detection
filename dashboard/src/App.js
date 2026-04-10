// =============================================================================
//  Traffic Violation Detection System
//  FILE: src/App.js
//  Main app with routing between Dashboard and Upload pages
// =============================================================================

import React, { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route, NavLink } from "react-router-dom";
import Dashboard from "./components/Dashboard";
import ViolationList from "./components/ViolationList";
import UploadVideo from "./components/UploadVideo";
import VehicleSearch from "./components/VehicleSearch";
import "./App.css";

function App() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch("/api/violations/stats/")
      .then(r => r.json())
      .then(setStats)
      .catch(() => {});
  }, []);

  return (
    <Router>
      <div className="app">
        {/* ── Sidebar ── */}
        <aside className="sidebar">
          <div className="sidebar-brand">
            <div className="brand-icon">
              <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                <rect width="28" height="28" rx="8" fill="#E63946"/>
                <path d="M6 20 L14 8 L22 20 Z" fill="white" opacity="0.9"/>
                <circle cx="14" cy="17" r="2" fill="#E63946"/>
              </svg>
            </div>
            <div>
              <div className="brand-name">TrafficWatch</div>
              <div className="brand-sub">Violation Detection</div>
            </div>
          </div>

          <nav className="sidebar-nav">
            <NavLink to="/" end className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
              <span className="nav-icon">◈</span>
              <span>Dashboard</span>
            </NavLink>
            <NavLink to="/violations" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
              <span className="nav-icon">⚠</span>
              <span>Violations</span>
              {stats?.total_violations > 0 && (
                <span className="nav-badge">{stats.total_violations}</span>
              )}
            </NavLink>
            <NavLink to="/search" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
              <span className="nav-icon">◎</span>
              <span>Search Plate</span>
            </NavLink>
            <NavLink to="/upload" className={({isActive}) => isActive ? "nav-item active" : "nav-item"}>
              <span className="nav-icon">↑</span>
              <span>Upload Video</span>
            </NavLink>
          </nav>

          <div className="sidebar-footer">
            <div className="api-status">
              <span className="status-dot"></span>
              <span>API Connected</span>
            </div>
            <div className="api-url">127.0.0.1:8000</div>
          </div>
        </aside>

        {/* ── Main content ── */}
        <main className="main-content">
          <Routes>
            <Route path="/"           element={<Dashboard />} />
            <Route path="/violations" element={<ViolationList />} />
            <Route path="/search"     element={<VehicleSearch />} />
            <Route path="/upload"     element={<UploadVideo />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
