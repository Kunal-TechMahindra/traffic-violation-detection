// =============================================================================
//  FILE: src/components/ViolationList.js
//  Full violations list with filtering and pagination
// =============================================================================

import React, { useState, useEffect, useCallback } from "react";

export default function ViolationList() {
  const [violations, setViolations] = useState([]);
  const [loading, setLoading]       = useState(true);
  const [search, setSearch]         = useState("");
  const [minSpeed, setMinSpeed]     = useState("");
  const [count, setCount]           = useState(0);
  const [page, setPage]             = useState(1);

  const load = useCallback(() => {
    setLoading(true);
    let url = `/api/violations/?page=${page}`;
    if (search)   url += `&plate=${search}`;
    if (minSpeed) url += `&min_speed=${minSpeed}`;

    fetch(url)
      .then(r => r.json())
      .then(data => {
        setViolations(data.results || []);
        setCount(data.count || 0);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [page, search, minSpeed]);

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.ceil(count / 20);

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">All Violations</h1>
        <p className="page-subtitle">{count} total records found</p>
      </div>

      {/* ── Filters ── */}
      <div className="card" style={{ padding: 16 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <input
            className="search-input"
            style={{ flex: 2 }}
            placeholder="Filter by plate number..."
            value={search}
            onChange={e => { setSearch(e.target.value); setPage(1); }}
          />
          <input
            className="search-input"
            style={{ flex: 1 }}
            type="number"
            placeholder="Min speed (km/h)"
            value={minSpeed}
            onChange={e => { setMinSpeed(e.target.value); setPage(1); }}
          />
          <button className="btn btn-outline" onClick={() => { setSearch(""); setMinSpeed(""); setPage(1); }}>
            Clear
          </button>
          <button className="btn btn-primary" onClick={load}>
            Refresh
          </button>
        </div>
      </div>

      {/* ── Table ── */}
      <div className="card">
        {loading ? (
          <div className="spinner" />
        ) : violations.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">⚠</div>
            <div className="empty-text">No violations found</div>
          </div>
        ) : (
          <>
            <table className="violations-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Plate</th>
                  <th>Vehicle</th>
                  <th>Speed</th>
                  <th>Over Limit</th>
                  <th>Frame</th>
                  <th>Timestamp</th>
                  <th>Video</th>
                </tr>
              </thead>
              <tbody>
                {violations.map((v, i) => (
                  <tr key={v.id}>
                    <td style={{ fontFamily: "DM Mono", color: "#4a5568", fontSize: 12 }}>
                      #{v.id}
                    </td>
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
                      +{(v.overspeed_by ?? (v.speed - 80)).toFixed(1)} km/h
                    </td>
                    <td style={{ fontFamily: "DM Mono", fontSize: 12, color: "#4a5568" }}>
                      {v.frame_number}
                    </td>
                    <td style={{ fontSize: 12, color: "#4a5568" }}>
                      {new Date(v.timestamp).toLocaleString()}
                    </td>
                    <td style={{ fontSize: 11, color: "#4a5568", maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {v.video_source}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* Pagination */}
            {totalPages > 1 && (
              <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 20 }}>
                <button className="btn btn-outline" disabled={page === 1} onClick={() => setPage(p => p - 1)}>
                  ← Prev
                </button>
                <span style={{ color: "#8892a4", padding: "10px 16px", fontSize: 13 }}>
                  Page {page} of {totalPages}
                </span>
                <button className="btn btn-outline" disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
