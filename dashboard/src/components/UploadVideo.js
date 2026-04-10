// =============================================================================
//  FILE: src/components/UploadVideo.js
//  Upload a video → trigger Celery task → poll progress
// =============================================================================

import React, { useState, useRef, useEffect } from "react";

export default function UploadVideo() {
  const [file, setFile]         = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [job, setJob]           = useState(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus]     = useState("");
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState("");
  const inputRef                = useRef();
  const pollRef                 = useRef();

  // Poll job status every 3 seconds
  useEffect(() => {
    if (!job) return;
    pollRef.current = setInterval(() => {
      fetch(`/api/job/${job}/`)
        .then(r => r.json())
        .then(data => {
          setProgress(data.progress || 0);
          setStatus(data.status);
          if (data.status === "completed") {
            clearInterval(pollRef.current);
            setResult(data.result);
            setUploading(false);
          }
          if (data.status === "failed") {
            clearInterval(pollRef.current);
            setError("Processing failed. Check Celery terminal for details.");
            setUploading(false);
          }
        })
        .catch(() => {});
    }, 3000);
    return () => clearInterval(pollRef.current);
  }, [job]);

  const handleDrop = e => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  };

  const upload = () => {
    if (!file) return;
    setUploading(true);
    setError("");
    setResult(null);
    setProgress(0);
    setStatus("uploading");

    const formData = new FormData();
    formData.append("video", file);

    fetch("/api/process-video/", { method: "POST", body: formData })
      .then(r => r.json())
      .then(data => {
        if (data.status === "queued") {
          setJob(data.job_id);
          setStatus("queued");
        } else {
          setError(data.error || data.message || "Upload failed");
          setUploading(false);
        }
      })
      .catch(e => { setError(e.message); setUploading(false); });
  };

  const statusLabel = {
    uploading : "Uploading video...",
    queued    : "Queued — waiting for worker...",
    processing: "Processing video...",
    completed : "Done!",
    failed    : "Failed",
  };

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Upload Video</h1>
        <p className="page-subtitle">Upload a traffic video to detect speed violations</p>
      </div>

      {/* ── Drop zone ── */}
      <div
        className={`upload-zone ${dragOver ? "drag-over" : ""}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.avi,.mov,.mkv"
          style={{ display: "none" }}
          onChange={e => setFile(e.target.files[0])}
        />
        <div className="upload-icon">↑</div>
        {file ? (
          <>
            <div className="upload-title" style={{ color: "#00b4d8" }}>{file.name}</div>
            <div className="upload-hint">{(file.size / 1024 / 1024).toFixed(1)} MB — click to change</div>
          </>
        ) : (
          <>
            <div className="upload-title">Drop video here or click to browse</div>
            <div className="upload-hint">Supports MP4, AVI, MOV, MKV</div>
          </>
        )}
      </div>

      {/* ── Upload button ── */}
      {file && !uploading && !result && (
        <div style={{ marginTop: 16, display: "flex", gap: 12 }}>
          <button className="btn btn-primary" onClick={upload}>
            ↑ Start Processing
          </button>
          <button className="btn btn-outline" onClick={() => setFile(null)}>
            Remove
          </button>
        </div>
      )}

      {/* ── Progress ── */}
      {uploading && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="card-title">Processing</div>
          <div style={{ color: "#8892a4", marginBottom: 8, fontSize: 13 }}>
            {statusLabel[status] || status}
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div style={{ fontFamily: "DM Mono", fontSize: 12, color: "#4a5568", textAlign: "right" }}>
            {progress}%
          </div>
          <div style={{ marginTop: 12, fontSize: 12, color: "#4a5568" }}>
            Job ID: <span style={{ fontFamily: "DM Mono", color: "#8892a4" }}>{job}</span>
          </div>
          <div style={{ marginTop: 4, fontSize: 12, color: "#4a5568" }}>
            Watch Terminal 2 (Celery) for live processing logs
          </div>
        </div>
      )}

      {/* ── Error ── */}
      {error && <div className="alert-banner" style={{ marginTop: 16 }}>⚠ {error}</div>}

      {/* ── Result ── */}
      {result && (
        <div className="card" style={{ marginTop: 24 }}>
          <div className="success-banner">
            Processing complete!
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
            {[
              { label: "Frames processed",  value: result.total_frames },
              { label: "Vehicles tracked",  value: result.total_vehicles },
              { label: "Speeds calculated", value: result.speeds_calculated },
              { label: "Violations found",  value: result.violations_found, alert: true },
              { label: "Highest speed",     value: `${result.highest_speed} km/h` },
              { label: "Average speed",     value: `${result.average_speed} km/h` },
            ].map(({ label, value, alert }) => (
              <div key={label} style={{ background: "#111827", borderRadius: 8, padding: "14px 16px" }}>
                <div style={{ fontSize: 11, color: "#4a5568", textTransform: "uppercase", letterSpacing: "0.8px", marginBottom: 6 }}>
                  {label}
                </div>
                <div style={{ fontFamily: "DM Mono", fontSize: 20, fontWeight: 700, color: alert ? "#e63946" : "#e8eaf6" }}>
                  {value}
                </div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 16, display: "flex", gap: 12 }}>
            <button className="btn btn-primary" onClick={() => window.location.href = "/violations"}>
              View Violations →
            </button>
            <button className="btn btn-outline" onClick={() => { setFile(null); setResult(null); setJob(null); }}>
              Upload Another
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
