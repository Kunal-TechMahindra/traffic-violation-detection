// =============================================================================
//  FILE: src/components/VehicleSearch.js
//  Search violations by license plate number
// =============================================================================

import React, { useState } from "react";

export default function VehicleSearch() {
  const [plate, setPlate]       = useState("");
  const [results, setResults]   = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState("");

  const search = () => {
    if (!plate.trim()) return;
    setLoading(true);
    setError("");
    setResults(null);

    fetch(`/api/vehicle/${plate.trim().toUpperCase()}/`)
      .then(r => {
        if (r.status === 404) throw new Error("No violations found for this plate");
        return r.json();
      })
      .then(data => { setResults(data); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Search by Plate</h1>
        <p className="page-subtitle">Look up all violations for any license plate</p>
      </div>

      <div className="card">
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <input
            className="search-input"
            placeholder="Enter plate number e.g. 34AIE791"
            value={plate}
            onChange={e => setPlate(e.target.value.toUpperCase())}
            onKeyDown={e => e.key === "Enter" && search()}
            style={{ flex: 1, textTransform: "uppercase", letterSpacing: "2px" }}
          />
          <button className="btn btn-primary" onClick={search} disabled={loading}>
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert-banner">⚠ {error}</div>
      )}

      {results && (
        <div className="card">
          <div style={{ marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <span className="plate-badge" style={{ fontSize: 16, padding: "6px 16px" }}>
                {results.plate}
              </span>
            </div>
            <div style={{ fontFamily: "DM Mono", color: "#e63946", fontSize: 18, fontWeight: 700 }}>
              {results.total_violations} violation{results.total_violations !== 1 ? "s" : ""}
            </div>
          </div>

          <table className="violations-table">
            <thead>
              <tr>
                <th>Speed</th>
                <th>Over Limit</th>
                <th>Vehicle</th>
                <th>Frame</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {results.violations.map(v => (
                <tr key={v.id}>
                  <td>
                    <span className="speed-badge violation">{v.speed} km/h</span>
                  </td>
                  <td style={{ fontFamily: "DM Mono", color: "#e63946" }}>
                    +{(v.overspeed_by ?? (v.speed - 80)).toFixed(1)} km/h
                  </td>
                  <td>
                    <span className={`type-pill ${(v.vehicle_type || "car").toLowerCase()}`}>
                      {v.vehicle_type || "Vehicle"}
                    </span>
                  </td>
                  <td style={{ fontFamily: "DM Mono", fontSize: 12, color: "#4a5568" }}>
                    {v.frame_number}
                  </td>
                  <td style={{ fontSize: 12, color: "#4a5568" }}>
                    {new Date(v.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
