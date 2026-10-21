import React, { useState } from 'react';
import type { UpstreamConfig } from '../types';
import { createUpstream, deleteUpstream } from '../api';
import { Plus, Trash2, Server } from 'lucide-react';

interface UpstreamsManagerProps {
  upstreams: UpstreamConfig[];
  onRefresh: () => void;
}

export const UpstreamsManager: React.FC<UpstreamsManagerProps> = ({ upstreams, onRefresh }) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [targetUrl, setTargetUrl] = useState('');
  const [timeoutMs, setTimeoutMs] = useState(5000);
  const [healthCheckPath, setHealthCheckPath] = useState('/healthz');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!id || !targetUrl) {
      setError('Upstream ID and Target URL are required.');
      return;
    }
    setLoading(true);
    try {
      await createUpstream({
        id: id.trim(),
        name: name.trim() || id.trim(),
        target_url: targetUrl.trim(),
        timeout_ms: Number(timeoutMs) || 5000,
        health_check_path: healthCheckPath.trim() || '/healthz',
      });
      setShowAddForm(false);
      setId('');
      setName('');
      setTargetUrl('');
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Failed to create upstream in MongoDB');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (upstreamId: string) => {
    if (!window.confirm(`Delete upstream '${upstreamId}' from MongoDB?`)) return;
    try {
      await deleteUpstream(upstreamId);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to delete upstream');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Server size={18} color="var(--primary)" />
            Upstream Backend Services
          </h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Configured target services stored in MongoDB ({upstreams.length} total)
          </span>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn-primary"
          style={{ fontSize: '0.8rem', padding: '8px 14px' }}
        >
          <Plus size={15} />
          {showAddForm ? 'Cancel' : 'Add Upstream'}
        </button>
      </div>

      {showAddForm && (
        <form
          onSubmit={handleCreate}
          className="glass-panel"
          style={{ padding: '20px', marginBottom: '20px', background: 'rgba(15, 23, 42, 0.9)' }}
        >
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '14px' }}>Register New Upstream</h3>
          {error && (
            <div style={{ color: 'var(--color-deny)', fontSize: '0.8rem', marginBottom: '12px' }}>
              {error}
            </div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', marginBottom: '16px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Upstream ID *
              </label>
              <input
                type="text"
                placeholder="e.g. ups_billing"
                value={id}
                onChange={(e) => setId(e.target.value)}
                className="mono"
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Name
              </label>
              <input
                type="text"
                placeholder="e.g. Billing Backend"
                value={name}
                onChange={(e) => setName(e.target.value)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Target Base URL *
              </label>
              <input
                type="text"
                placeholder="e.g. http://localhost:8080"
                value={targetUrl}
                onChange={(e) => setTargetUrl(e.target.value)}
                className="mono"
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
                required
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Timeout (ms)
              </label>
              <input
                type="number"
                value={timeoutMs}
                onChange={(e) => setTimeoutMs(Number(e.target.value))}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Health Check Path
              </label>
              <input
                type="text"
                value={healthCheckPath}
                onChange={(e) => setHealthCheckPath(e.target.value)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
              />
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="tab-btn"
              style={{ border: '1px solid var(--card-border)' }}
            >
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'Saving to MongoDB...' : 'Save Upstream'}
            </button>
          </div>
        </form>
      )}

      <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Name</th>
                <th>Target URL</th>
                <th>Timeout</th>
                <th>Health Path</th>
                <th style={{ width: '80px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {upstreams.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '28px', color: 'var(--text-dim)' }}>
                    No upstreams configured in MongoDB. Click "Add Upstream" to register one.
                  </td>
                </tr>
              ) : (
                upstreams.map((ups) => (
                  <tr key={ups.id}>
                    <td>
                      <span className="mono" style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--primary)' }}>
                        {ups.id}
                      </span>
                    </td>
                    <td>{ups.name}</td>
                    <td>
                      <span className="mono" style={{ fontSize: '0.8rem' }}>{ups.target_url}</span>
                    </td>
                    <td>{ups.timeout_ms}ms</td>
                    <td>
                      <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                        {ups.health_check_path}
                      </span>
                    </td>
                    <td>
                      <button onClick={() => handleDelete(ups.id)} className="btn-danger" style={{ padding: '4px 8px' }}>
                        <Trash2 size={13} />
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
