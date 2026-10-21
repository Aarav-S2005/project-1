import React, { useState } from 'react';
import type { MiddlewareConfig } from '../types';
import { createMiddleware, updateMiddleware, deleteMiddleware } from '../api';
import {
  Plus,
  Trash2,
  Cpu,
  ToggleLeft,
  ToggleRight,
  ShieldAlert,
  ShieldCheck,
  Key,
  Clock,
  Layers,
  Hash,
  FileText,
  Sliders,
  Check,
  Sparkles,
} from 'lucide-react';

interface MiddlewaresManagerProps {
  middlewares: MiddlewareConfig[];
  onRefresh: () => void;
}

export interface MiddlewareTemplate {
  key: string;
  id: string;
  name: string;
  type: string;
  category: 'Security' | 'Access Control' | 'Traffic Control' | 'Observability' | 'Utilities';
  description: string;
  defaultOrder: number;
  config: Record<string, any>;
}

export const PRECONFIGURED_MIDDLEWARES: MiddlewareTemplate[] = [
  {
    key: 'trust_score_evaluator',
    id: 'mw_trust_scorer',
    name: 'Zero-Trust Anomaly Scorer',
    type: 'trust_score_evaluator',
    category: 'Security',
    description: 'Extracts behavioral features (rate, geo-velocity, TLS/fingerprint) & graph traversal novelty, evaluates via Isolation Forest, and decays trust in Redis.',
    defaultOrder: 1,
    config: {
      half_life_seconds: 300.0,
      anomaly_weight: 0.4,
    },
  },
  {
    key: 'rebac_authorizer',
    id: 'mw_rebac_authorizer',
    name: 'SpiceDB ReBAC Authorizer',
    type: 'rebac_authorizer',
    category: 'Access Control',
    description: 'Enforces relationship graph checks in SpiceDB. Automatically writes narrow restriction tuples into the graph when trust score drops.',
    defaultOrder: 2,
    config: {
      narrow_ttl_seconds: 60,
      enforce_rebac: true,
    },
  },
  {
    key: 'jwt_auth',
    id: 'mw_jwt_auth',
    name: 'JWT Bearer Authenticator',
    type: 'jwt_auth',
    category: 'Security',
    description: 'Validates Bearer tokens in Authorization header, decodes cryptographic signatures, and extracts user identity/claims into request context.',
    defaultOrder: 0,
    config: {
      header_name: 'Authorization',
      subject_claim: 'sub',
      require_valid: true,
    },
  },
  {
    key: 'rate_limit',
    id: 'mw_rate_limiter',
    name: 'Redis Sliding Rate Limiter',
    type: 'rate_limit',
    category: 'Traffic Control',
    description: 'Sliding-window rate limiter backed by Redis. Throttles high-frequency bursts per IP or Subject.',
    defaultOrder: 3,
    config: {
      max_requests: 60,
      window_seconds: 60,
    },
  },
  {
    key: 'cors',
    id: 'mw_cors_handler',
    name: 'CORS Policy Enforcer',
    type: 'cors',
    category: 'Utilities',
    description: 'Configures cross-origin resource sharing headers for browser clients (allowed origins, methods, headers).',
    defaultOrder: 4,
    config: {
      allow_origins: ['*'],
      allow_methods: ['GET', 'POST', 'PUT', 'DELETE'],
      allow_headers: ['*'],
      allow_credentials: true,
    },
  },
  {
    key: 'request_id',
    id: 'mw_request_id',
    name: 'Request ID Tracing',
    type: 'request_id',
    category: 'Observability',
    description: 'Injects a unique UUID X-Request-ID into every incoming and proxied upstream request for end-to-end tracing.',
    defaultOrder: 5,
    config: {
      header_name: 'X-Request-ID',
    },
  },
  {
    key: 'logger',
    id: 'mw_audit_logger',
    name: 'MongoDB Audit & SHAP Logger',
    type: 'logger',
    category: 'Observability',
    description: 'Asynchronously buffers and streams request decision records, trust transitions, and SHAP explainability attribution to MongoDB.',
    defaultOrder: 6,
    config: {
      async_batch: true,
      log_payload: false,
    },
  },
  {
    key: 'ip_filter',
    id: 'mw_ip_filter',
    name: 'Client IP / Subnet Filter',
    type: 'ip_filter',
    category: 'Security',
    description: 'Restricts gateway entry to specified IP addresses or CIDR blocks, blocking unauthorized networks.',
    defaultOrder: 7,
    config: {
      allow_cidrs: ['0.0.0.0/0'],
      block_private_ips: false,
    },
  },
];

export const MiddlewaresManager: React.FC<MiddlewaresManagerProps> = ({ middlewares, onRefresh }) => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedTemplateKey, setSelectedTemplateKey] = useState<string>('trust_score_evaluator');
  const [id, setId] = useState('');
  const [name, setName] = useState('');
  const [type, setType] = useState('');
  const [order, setOrder] = useState(1);
  const [isActive, setIsActive] = useState(true);
  const [configJson, setConfigJson] = useState('{\n  "enabled": true\n}');
  const [customMode, setCustomMode] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Apply a template to form fields
  const applyTemplate = (template: MiddlewareTemplate) => {
    setSelectedTemplateKey(template.key);
    setCustomMode(false);
    // Ensure unique ID if already present
    let candidateId = template.id;
    if (middlewares.some((m) => m.id === candidateId)) {
      candidateId = `${template.id}_${Date.now().toString().slice(-4)}`;
    }
    setId(candidateId);
    setName(template.name);
    setType(template.type);
    setOrder(template.defaultOrder);
    setConfigJson(JSON.stringify(template.config, null, 2));
    setError(null);
  };

  const handleOpenAddForm = (template?: MiddlewareTemplate) => {
    const t = template || PRECONFIGURED_MIDDLEWARES[0];
    applyTemplate(t);
    setShowAddForm(true);
  };

  const handleSelectDropdownChange = (key: string) => {
    if (key === '__custom__') {
      setSelectedTemplateKey('__custom__');
      setCustomMode(true);
      setId('');
      setName('');
      setType('');
      setOrder(middlewares.length + 1);
      setConfigJson('{\n  "custom_param": true\n}');
      return;
    }
    const t = PRECONFIGURED_MIDDLEWARES.find((item) => item.key === key);
    if (t) {
      applyTemplate(t);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!id || !name || !type) {
      setError('Middleware ID, Name, and Type are required.');
      return;
    }

    let parsedConfig = {};
    try {
      parsedConfig = JSON.parse(configJson || '{}');
    } catch {
      setError('Invalid JSON in Configuration field.');
      return;
    }

    setLoading(true);
    try {
      await createMiddleware({
        id: id.trim(),
        name: name.trim(),
        type: type.trim(),
        order: Number(order) || 1,
        is_active: isActive,
        config: parsedConfig,
      });
      setShowAddForm(false);
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Failed to create middleware in MongoDB');
    } finally {
      setLoading(false);
    }
  };

  const handleToggle = async (mw: MiddlewareConfig) => {
    try {
      await updateMiddleware(mw.id, {
        ...mw,
        is_active: !mw.is_active,
      });
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to update middleware');
    }
  };

  const handleDelete = async (mwId: string) => {
    if (!window.confirm(`Delete middleware '${mwId}' from MongoDB?`)) return;
    try {
      await deleteMiddleware(mwId);
      onRefresh();
    } catch (err: any) {
      alert(err.message || 'Failed to delete middleware');
    }
  };

  const getTemplateIcon = (key: string) => {
    switch (key) {
      case 'trust_score_evaluator':
        return <ShieldAlert size={16} color="var(--primary)" />;
      case 'rebac_authorizer':
        return <ShieldCheck size={16} color="var(--color-allow)" />;
      case 'jwt_auth':
        return <Key size={16} color="#fbbf24" />;
      case 'rate_limit':
        return <Clock size={16} color="#38bdf8" />;
      case 'cors':
        return <Layers size={16} color="#a78bfa" />;
      case 'request_id':
        return <Hash size={16} color="#f472b6" />;
      case 'logger':
        return <FileText size={16} color="#34d399" />;
      case 'ip_filter':
        return <Sliders size={16} color="#fb923c" />;
      default:
        return <Cpu size={16} color="var(--primary)" />;
    }
  };

  const activeTemplate = PRECONFIGURED_MIDDLEWARES.find((t) => t.key === selectedTemplateKey);

  return (
    <div>
      {/* Title & Add Button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={18} color="var(--primary)" />
            Gateway Middlewares Pipeline
          </h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Configured execution chain stored in MongoDB ({middlewares.length} active in pipeline)
          </span>
        </div>
        <button
          onClick={() => (showAddForm ? setShowAddForm(false) : handleOpenAddForm())}
          className="btn-primary"
          style={{ fontSize: '0.8rem', padding: '8px 14px' }}
        >
          <Plus size={15} />
          {showAddForm ? 'Cancel' : 'Add Middleware'}
        </button>
      </div>

      {/* Preset Catalog / Selection Banner when Add Form is open */}
      {showAddForm && (
        <div className="glass-panel" style={{ padding: '20px', marginBottom: '24px', background: 'rgba(15, 23, 42, 0.95)', border: '1px solid var(--primary)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', borderBottom: '1px solid var(--card-border)', paddingBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={18} color="var(--primary)" />
              <h3 style={{ fontSize: '1rem', fontWeight: 600, margin: 0 }}>
                Select a Pre-configured Middleware
              </h3>
            </div>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Click any template to auto-populate configuration
            </span>
          </div>

          {/* Quick Select Cards Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
              gap: '10px',
              marginBottom: '20px',
            }}
          >
            {PRECONFIGURED_MIDDLEWARES.map((tmpl) => {
              const isSelected = selectedTemplateKey === tmpl.key && !customMode;
              const alreadyInPipeline = middlewares.some((m) => m.type === tmpl.type);

              return (
                <div
                  key={tmpl.key}
                  onClick={() => applyTemplate(tmpl)}
                  style={{
                    background: isSelected ? 'rgba(99, 102, 241, 0.18)' : 'rgba(15, 23, 42, 0.7)',
                    border: isSelected ? '1px solid var(--primary)' : '1px solid var(--card-border)',
                    borderRadius: '8px',
                    padding: '12px',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                    position: 'relative',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {getTemplateIcon(tmpl.key)}
                      <span style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff' }}>
                        {tmpl.name}
                      </span>
                    </div>
                    {isSelected && <Check size={14} color="var(--primary)" />}
                  </div>

                  <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', margin: '0 0 8px 0', lineHeight: 1.35 }}>
                    {tmpl.description}
                  </p>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.68rem' }}>
                    <span
                      style={{
                        background: 'rgba(255, 255, 255, 0.08)',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        color: 'var(--text-dim)',
                      }}
                    >
                      {tmpl.category}
                    </span>
                    {alreadyInPipeline ? (
                      <span style={{ color: 'var(--color-allow)', fontWeight: 600 }}>✓ In Pipeline</span>
                    ) : (
                      <span style={{ color: 'var(--text-dim)' }}>Priority #{tmpl.defaultOrder}</span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Form to Review & Confirm */}
          <form onSubmit={handleCreate}>
            <div style={{ background: 'rgba(0, 0, 0, 0.35)', padding: '16px', borderRadius: '8px', border: '1px solid var(--card-border)', marginBottom: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>
                  Configuration Review & Customization
                </span>
                {activeTemplate && !customMode && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--primary)', background: 'rgba(99, 102, 241, 0.1)', padding: '2px 8px', borderRadius: '4px' }}>
                    Selected: {activeTemplate.name} ({activeTemplate.type})
                  </span>
                )}
              </div>

              {error && (
                <div style={{ color: 'var(--color-deny)', fontSize: '0.8rem', marginBottom: '12px' }}>
                  {error}
                </div>
              )}

              {/* Template Dropdown Selector for Fast Switching */}
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                  Choose Middleware Template
                </label>
                <select
                  value={customMode ? '__custom__' : selectedTemplateKey}
                  onChange={(e) => handleSelectDropdownChange(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    background: '#0b0f17',
                    border: '1px solid var(--card-border)',
                    color: '#fff',
                    fontSize: '0.85rem',
                  }}
                >
                  <optgroup label="Security & Access Control">
                    <option value="trust_score_evaluator">Zero-Trust Anomaly Scorer (trust_score_evaluator)</option>
                    <option value="rebac_authorizer">SpiceDB ReBAC Authorizer (rebac_authorizer)</option>
                    <option value="jwt_auth">JWT Bearer Authenticator (jwt_auth)</option>
                    <option value="ip_filter">Client IP / Subnet Filter (ip_filter)</option>
                  </optgroup>
                  <optgroup label="Traffic & Performance">
                    <option value="rate_limit">Redis Sliding Rate Limiter (rate_limit)</option>
                  </optgroup>
                  <optgroup label="Observability & Utilities">
                    <option value="logger">MongoDB Audit & SHAP Logger (logger)</option>
                    <option value="request_id">Request ID Tracing (request_id)</option>
                    <option value="cors">CORS Policy Enforcer (cors)</option>
                  </optgroup>
                  <optgroup label="Manual">
                    <option value="__custom__">Custom Middleware (Write Custom Type)...</option>
                  </optgroup>
                </select>
              </div>

              {/* Fields Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', marginBottom: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Middleware ID *
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. mw_rate_limiter"
                    value={id}
                    onChange={(e) => setId(e.target.value)}
                    className="mono"
                    style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
                    required
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Display Name *
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Redis Rate Limiter"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
                    required
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Middleware Type *
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. rate_limit"
                    value={type}
                    onChange={(e) => setType(e.target.value)}
                    className="mono"
                    style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
                    required
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                    Execution Priority (Order)
                  </label>
                  <input
                    type="number"
                    value={order}
                    onChange={(e) => setOrder(Number(e.target.value))}
                    style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
                  />
                </div>
              </div>

              {/* JSON Configuration */}
              <div style={{ marginBottom: '14px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <label style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    Configuration Parameters (JSON)
                  </label>
                  <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                    Auto-generated default for {name || type || 'middleware'}
                  </span>
                </div>
                <textarea
                  rows={4}
                  value={configJson}
                  onChange={(e) => setConfigJson(e.target.value)}
                  className="mono"
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: '6px',
                    background: '#0b0f17',
                    border: '1px solid var(--card-border)',
                    color: '#a5b4fc',
                    fontSize: '0.8rem',
                    resize: 'vertical',
                  }}
                />
              </div>

              {/* Actions */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={isActive}
                    onChange={(e) => setIsActive(e.target.checked)}
                  />
                  Enable Middleware Immediately
                </label>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    onClick={() => setShowAddForm(false)}
                    className="tab-btn"
                    style={{ border: '1px solid var(--card-border)' }}
                  >
                    Cancel
                  </button>
                  <button type="submit" disabled={loading} className="btn-primary">
                    {loading ? 'Saving to MongoDB...' : 'Save to MongoDB'}
                  </button>
                </div>
              </div>
            </div>
          </form>
        </div>
      )}

      {/* Middlewares Table */}
      <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th style={{ width: '60px' }}>Order</th>
                <th>Name & ID</th>
                <th>Type</th>
                <th>Status</th>
                <th>Configuration</th>
                <th style={{ width: '120px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {middlewares.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-dim)' }}>
                    No custom middlewares configured in MongoDB. Click "Add Middleware" above to select and enable one.
                  </td>
                </tr>
              ) : (
                middlewares
                  .sort((a, b) => a.order - b.order)
                  .map((mw) => (
                    <tr key={mw.id}>
                      <td>
                        <span className="mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)' }}>
                          #{mw.order}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {getTemplateIcon(mw.type)}
                          <div>
                            <span style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '0.85rem' }}>{mw.name}</span>
                            <span style={{ display: 'block', fontSize: '0.7rem', color: 'var(--text-dim)' }} className="mono">
                              {mw.id}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <span
                          className="mono"
                          style={{
                            fontSize: '0.78rem',
                            color: '#a5b4fc',
                            background: 'rgba(99, 102, 241, 0.1)',
                            padding: '2px 8px',
                            borderRadius: '4px',
                          }}
                        >
                          {mw.type}
                        </span>
                      </td>
                      <td>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            color: mw.is_active ? 'var(--color-allow)' : 'var(--text-dim)',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                          }}
                        >
                          <span
                            style={{
                              width: '6px',
                              height: '6px',
                              borderRadius: '50%',
                              backgroundColor: mw.is_active ? 'var(--color-allow)' : 'var(--text-dim)',
                            }}
                          />
                          {mw.is_active ? 'Active' : 'Disabled'}
                        </span>
                      </td>
                      <td>
                        <pre className="mono" style={{ fontSize: '0.7rem', color: 'var(--text-dim)', margin: 0, maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={JSON.stringify(mw.config, null, 2)}>
                          {JSON.stringify(mw.config)}
                        </pre>
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '6px' }}>
                          <button
                            onClick={() => handleToggle(mw)}
                            className="tab-btn"
                            style={{ padding: '4px 8px', fontSize: '0.75rem', border: '1px solid var(--card-border)' }}
                            title={mw.is_active ? 'Disable Middleware' : 'Activate Middleware'}
                          >
                            {mw.is_active ? <ToggleRight size={15} color="var(--color-allow)" /> : <ToggleLeft size={15} />}
                          </button>
                          <button
                            onClick={() => handleDelete(mw.id)}
                            className="btn-danger"
                            style={{ padding: '4px 8px' }}
                            title="Delete from MongoDB"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
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

export default MiddlewaresManager;
