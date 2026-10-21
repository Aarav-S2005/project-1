import React, { useState } from 'react';
import type { RouteConfig, UpstreamConfig } from '../types';
import { createRoute, deleteRoute } from '../api';
import { Plus, Trash2, Network, Shield, ShieldOff } from 'lucide-react';

interface RoutesManagerProps {
  routes: RouteConfig[];
  upstreams: UpstreamConfig[];
  onRefresh: () => void;
}

export const RoutesManager: React.FC<RoutesManagerProps> = ({ routes, upstreams, onRefresh }) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [id, setId] = useState('');
  const [upstreamId, setUpstreamId] = useState('');
  const [pathPrefix, setPathPrefix] = useState('');
  const [methods, setMethods] = useState<string[]>(['GET']);
  const [authRequired, setAuthRequired] = useState(true);
  const [resourceType, setResourceType] = useState('document');
  const [idExtractor, setIdExtractor] = useState('path_param:id');
  const [stripPath, setStripPath] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleMethod = (m: string) => {
    setMethods((prev) =>
      prev.includes(m) ? prev.filter((item) => item !== m) : [...prev, m]
    );
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!id || !pathPrefix || !upstreamId) {
      setError('Route ID, Path Prefix, and Upstream are required.');
      return;
    }
    if (methods.length === 0) {
      setError('Select at least one allowed HTTP method.');
      return;
    }

    setLoading(true);
    try {
      await createRoute({
        id: id.trim(),
        upstream_id: upstreamId.trim(),
        path_prefix: pathPrefix.trim(),
        methods,
        strip_path: stripPath,
        auth_required: authRequired,
        resource_type: resourceType.trim() || 'document',
        resource_id_extractor: idExtractor.trim() || 'path_param:id',
        permission_mapping: {
          GET: 'view',
          POST: 'create',
          PUT: 'edit',
          DELETE: 'delete',
        },
      });
      setShowAddForm(false);
      setId('');
      setPathPrefix('');
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Failed to save route in MongoDB');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (routeId: string) => {
    if (!window.confirm(`Delete route '${routeId}' from MongoDB?`)) return;
    try {
      await deleteRoute(routeId);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to delete route');
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Network size={18} color="var(--primary)" />
            Gateway Dynamic Routes
          </h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Routing rules and ReBAC policies stored in MongoDB ({routes.length} total)
          </span>
        </div>
        <button
          onClick={() => {
            if (!showAddForm && upstreams.length > 0 && !upstreamId) {
              setUpstreamId(upstreams[0].id);
            }
            setShowAddForm(!showAddForm);
          }}
          className="btn-primary"
          style={{ fontSize: '0.8rem', padding: '8px 14px' }}
        >
          <Plus size={15} />
          {showAddForm ? 'Cancel' : 'Add Route'}
        </button>
      </div>

      {showAddForm && (
        <form
          onSubmit={handleCreate}
          className="glass-panel"
          style={{ padding: '20px', marginBottom: '20px', background: 'rgba(15, 23, 42, 0.9)' }}
        >
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '14px' }}>Register New Gateway Route</h3>
          {error && (
            <div style={{ color: 'var(--color-deny)', fontSize: '0.8rem', marginBottom: '12px' }}>
              {error}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px', marginBottom: '14px' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Route ID *
              </label>
              <input
                type="text"
                placeholder="e.g. route_orders"
                value={id}
                onChange={(e) => setId(e.target.value)}
                className="mono"
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
                required
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Path Prefix *
              </label>
              <input
                type="text"
                placeholder="e.g. /api/v1/orders"
                value={pathPrefix}
                onChange={(e) => setPathPrefix(e.target.value)}
                className="mono"
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
                required
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Target Upstream *
              </label>
              <select
                value={upstreamId}
                onChange={(e) => setUpstreamId(e.target.value)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
                required
              >
                <option value="">-- Select Target Upstream --</option>
                {upstreams.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name} ({u.id})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                SpiceDB Resource Type
              </label>
              <select
                value={['document', 'organization', 'workspace'].includes(resourceType) ? resourceType : '__custom__'}
                onChange={(e) => {
                  if (e.target.value !== '__custom__') {
                    setResourceType(e.target.value);
                  } else {
                    setResourceType('');
                  }
                }}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem', marginBottom: '4px' }}
              >
                <option value="document">document (default schema)</option>
                <option value="organization">organization</option>
                <option value="workspace">workspace</option>
                <option value="__custom__">Custom type...</option>
              </select>
              {!['document', 'organization', 'workspace'].includes(resourceType) && (
                <input
                  type="text"
                  placeholder="Enter custom resource type"
                  value={resourceType}
                  onChange={(e) => setResourceType(e.target.value)}
                  className="mono"
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--primary)', color: '#fff', fontSize: '0.8rem' }}
                />
              )}
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Resource ID Extractor
              </label>
              <select
                value={['path_param:id', 'path_param:resource_id', 'query_param:id', 'header:X-Resource-ID'].includes(idExtractor) ? idExtractor : '__custom__'}
                onChange={(e) => {
                  if (e.target.value !== '__custom__') {
                    setIdExtractor(e.target.value);
                  } else {
                    setIdExtractor('');
                  }
                }}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem', marginBottom: '4px' }}
              >
                <option value="path_param:id">path_param:id (e.g. /documents/:id)</option>
                <option value="path_param:resource_id">path_param:resource_id</option>
                <option value="query_param:id">query_param:id (e.g. ?id=123)</option>
                <option value="header:X-Resource-ID">header:X-Resource-ID</option>
                <option value="__custom__">Custom extractor...</option>
              </select>
              {!['path_param:id', 'path_param:resource_id', 'query_param:id', 'header:X-Resource-ID'].includes(idExtractor) && (
                <input
                  type="text"
                  placeholder="e.g. path_param:custom_id"
                  value={idExtractor}
                  onChange={(e) => setIdExtractor(e.target.value)}
                  className="mono"
                  style={{ width: '100%', padding: '6px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--primary)', color: '#fff', fontSize: '0.8rem' }}
                />
              )}
            </div>
          </div>

          {/* Methods and Checkboxes */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', alignItems: 'center', marginBottom: '16px', background: 'rgba(0, 0, 0, 0.25)', padding: '12px 14px', borderRadius: '8px' }}>
            <div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginBottom: '6px' }}>Allowed Methods:</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                {['GET', 'POST', 'PUT', 'DELETE', 'PATCH'].map((m) => (
                  <label key={m} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={methods.includes(m)}
                      onChange={() => toggleMethod(m)}
                    />
                    {m}
                  </label>
                ))}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '16px', marginLeft: 'auto' }}>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={authRequired}
                  onChange={(e) => setAuthRequired(e.target.checked)}
                />
                Enforce Zero-Trust Trust Checks
              </label>
              <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={stripPath}
                  onChange={(e) => setStripPath(e.target.checked)}
                />
                Strip Path Prefix
              </label>
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
              {loading ? 'Saving to MongoDB...' : 'Save Route'}
            </button>
          </div>
        </form>
      )}

      {/* Routes Table */}
      <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Path Prefix</th>
                <th>Target Upstream</th>
                <th>Methods</th>
                <th>Zero-Trust Auth</th>
                <th>SpiceDB ReBAC</th>
                <th style={{ width: '80px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {routes.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '28px', color: 'var(--text-dim)' }}>
                    No routes configured in MongoDB. Click "Add Route" to register one.
                  </td>
                </tr>
              ) : (
                routes.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <div>
                        <span className="mono" style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--primary)' }}>
                          {r.path_prefix}
                        </span>
                        <span style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                          ID: {r.id} {r.strip_path ? '(strip_prefix)' : ''}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: '0.8rem' }}>{r.upstream_id}</span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '4px' }}>
                        {r.methods.map((m) => (
                          <span
                            key={m}
                            style={{
                              fontSize: '0.7rem',
                              padding: '2px 5px',
                              borderRadius: '4px',
                              background: 'rgba(255, 255, 255, 0.08)',
                              fontWeight: 600,
                            }}
                          >
                            {m}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>
                      {r.auth_required ? (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            color: 'var(--color-allow)',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                          }}
                        >
                          <Shield size={13} />
                          Enforced
                        </span>
                      ) : (
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            color: 'var(--text-dim)',
                            fontSize: '0.75rem',
                          }}
                        >
                          <ShieldOff size={13} />
                          Public
                        </span>
                      )}
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {r.resource_type}:{r.resource_id_extractor}
                      </span>
                    </td>
                    <td>
                      <button onClick={() => handleDelete(r.id)} className="btn-danger" style={{ padding: '4px 8px' }}>
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
