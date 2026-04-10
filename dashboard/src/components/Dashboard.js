// =============================================================================
//  FILE: src/components/Dashboard.js
//  Main dashboard — stats, speed chart, recent violations
// =============================================================================

import React, { useState, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell
} from "recharts";

const API = "";

export default function Dashboard() {
  const [stats, setStats]         = useState(null);
  const [violations, setViolations] = useState([]);
  const [loading, setLoading]     = useState(true);

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/violations/stats/`).then(r => r.json()),
      fetch(`${API}/api/violations/?page_size=8`).then(r => r.json()),
    ]).then(([s, v]) => {
      setStats(s);
      setViolations(v.results || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="spinner" />;

  // Build chart data from vehicle type breakdown
  const chartData = stats?.by_vehicle_type
    ? Object.entries(stats.by_vehicle_type).map(([name, count]) => ({ name, count }))
    : [];

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Command Center</h1>
        <p className="page-subtitle">Live traffic violation monitoring overview</p>
      </div>

      {/* ── Stat Cards ── */}
      <div className="stats-grid">
        <div className="stat-card alert">
          <div className="stat-label">Total Violations</div>
          <div className="stat-value">{stats?.total_violations ?? 0}</div>
          <div className="stat-unit">recorded</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Highest Speed</div>
          <div className="stat-value">{stats?.highest_speed ?? 0}</div>
          <div className="stat-unit">km/h</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Average Speed</div>
          <div className="stat-value">{stats?.average_speed ?? 0}</div>
          <div className="stat-unit">km/h</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Unique Plates</div>
          <div className="stat-value">{stats?.unique_plates ?? 0}</div>
          <div className="stat-unit">identified</div>
        </div>
      </div>

      <div className="grid-2">
        {/* ── Speed by vehicle type chart ── */}
        <div className="card">
          <div className="card-title">Violations by Vehicle Type</div>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={chartData} barSize={36}>
                <XAxis
                  dataKey="name"
                  tick={{ fill: "#8892a4", fontSize: 12, fontFamily: "DM Mono" }}
                  axisLine={false} tickLine={false}
                />
                <YAxis
                  tick={{ fill: "#8892a4", fontSize: 11, fontFamily: "DM Mono" }}
                  axisLine={false} tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#1a2235", border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 8, color: "#e8eaf6", fontFamily: "DM Mono"
                  }}
                  cursor={{ fill: "rgba(255,255,255,0.04)" }}
                />
                <Bar dataKey="count" radius={[4,4,0,0]}>
                  {chartData.map((_, i) => (
                    <Cell key={i} fill={["#e63946","#00b4d8","#f4a261","#2dc653"][i % 4]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">◈</div>
              <div className="empty-text">No data yet — process a video first</div>
            </div>
          )}
        </div>

        {/* ── Today summary ── */}
        <div className="card">
          <div className="card-title">Today's Summary</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {[
              { label: "Violations today",   value: stats?.today_violations ?? 0,  color: "#e63946" },
              { label: "Speed limit (km/h)",  value: 80,                            color: "#f4a261" },
              { label: "Lowest speed (km/h)", value: stats?.lowest_speed ?? 0,      color: "#2dc653" },
              { label: "Highest speed (km/h)",value: stats?.highest_speed ?? 0,     color: "#00b4d8" },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                <span style={{ fontSize: 13, color: "#8892a4" }}>{label}</span>
                <span style={{ fontFamily: "DM Mono", fontSize: 16, fontWeight: 700, color }}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Recent Violations Table ── */}
      <div className="card">
        <div className="card-title">Recent Violations</div>
        {violations.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">⚠</div>
            <div className="empty-text">No violations recorded yet</div>
          </div>
        ) : (
          <table className="violations-table">
            <thead>
              <tr>
                <th>Plate</th>
                <th>Vehicle</th>
                <th>Speed</th>
                <th>Over Limit</th>
                <th>Time</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {violations.map(v => (
                <tr key={v.id}>
                  <td><span className="plate-badge">{v.plate}</span></td>
                  <td>
                    <span className={`type-pill ${(v.vehicle_type || "car").toLowerCase()}`}>
                      {v.vehicle_type || "Vehicle"}
                    </span>
                  </td>
                  <td>
                    <span className={`speed-badge ${v.speed > 80 ? "violation" : "safe"}`}>
                      {v.speed} km/h
                    </span>
                  </td>
                  <td style={{ fontFamily: "DM Mono", color: "#e63946", fontSize: 13 }}>
                    +{v.overspeed_by ?? (v.speed - 80).toFixed(1)} km/h
                  </td>
                  <td style={{ fontSize: 12, color: "#4a5568" }}>
                    {new Date(v.timestamp).toLocaleTimeString()}
                  </td>
                  <td><span className="violation-tag">Violation</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
