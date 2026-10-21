import React, { useState } from 'react';
import type { AuditRecord, DecisionAction } from '../types';
import { ShapExplainer } from './ShapExplainer';
import { ChevronDown, ChevronRight, Search, Filter, ShieldCheck, AlertTriangle, KeyRound, Ban } from 'lucide-react';

interface AuditTableProps {
  records: AuditRecord[];
  total: number;
  selectedDecision: string;
  onSelectDecision: (decision: string) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
}

export const AuditTable: React.FC<AuditTableProps> = ({
  records,
  total,
  selectedDecision,
  onSelectDecision,
  searchQuery,
  onSearchChange,
}) => {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const getDecisionIcon = (decision: DecisionAction) => {
    switch (decision) {
      case 'allow':
        return <ShieldCheck size={14} color="var(--color-allow)" />;
      case 'narrow':
        return <AlertTriangle size={14} color="var(--color-narrow)" />;
      case 'step_up':
        return <KeyRound size={14} color="var(--color-step-up)" />;
      case 'deny':
        return <Ban size={14} color="var(--color-deny)" />;
    }
  };

  const filteredRecords = records.filter((r) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      r.session_id.toLowerCase().includes(q) ||
      r.subject_id.toLowerCase().includes(q) ||
      r.resource.toLowerCase().includes(q) ||
      r.route_id.toLowerCase().includes(q)
    );
  });

  return (
    <div>
      {/* Search and Filters Header */}
      <div
        className="glass-panel"
        style={{
          padding: '16px 20px',
          marginBottom: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '16px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, maxWidth: '450px' }}>
          <Search size={16} color="var(--text-dim)" />
          <input
            type="text"
            placeholder="Search by session, subject, resource..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              outline: 'none',
              color: 'var(--text-main)',
              fontSize: '0.875rem',
              width: '100%',
            }}
          />
          {total > 0 && (
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
              ({total} logs)
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            <Filter size={14} />
            <span>Filter:</span>
          </div>
          <div style={{ display: 'flex', gap: '6px' }}>
            {['ALL', 'allow', 'narrow', 'step_up', 'deny'].map((dec) => (
              <button
                key={dec}
                onClick={() => onSelectDecision(dec)}
                className={`tab-btn ${selectedDecision === dec ? 'active' : ''}`}
                style={{ padding: '6px 12px', fontSize: '0.75rem', textTransform: 'uppercase' }}
              >
                {dec}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Audit Records Table */}
      <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th style={{ width: '30px' }} />
                <th>Timestamp</th>
                <th>Subject Principal</th>
                <th>Session ID</th>
                <th>Resource & Method</th>
                <th>Trust Score</th>
                <th>Decision Action</th>
                <th>Latency</th>
              </tr>
            </thead>
            <tbody>
              {filteredRecords.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-dim)' }}>
                    No audit records match the current filter.
                  </td>
                </tr>
              ) : (
                filteredRecords.map((r) => {
                  const rowId = r.id || r._id || r.request_id;
                  const isExpanded = expandedId === rowId;
                  const delta = r.trust_score_after - r.trust_score_before;

                  return (
                    <React.Fragment key={rowId}>
                      <tr
                        onClick={() => toggleExpand(rowId)}
                        style={{ cursor: 'pointer', background: isExpanded ? 'rgba(99, 102, 241, 0.05)' : undefined }}
                      >
                        <td>
                          {isExpanded ? (
                            <ChevronDown size={14} color="var(--primary)" />
                          ) : (
                            <ChevronRight size={14} color="var(--text-dim)" />
                          )}
                        </td>
                        <td>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                            {new Date(r.timestamp).toLocaleTimeString()}
                          </span>
                        </td>
                        <td>
                          <span className="mono" style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                            {r.subject_id}
                          </span>
                        </td>
                        <td>
                          <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                            {r.session_id.slice(0, 16)}
                          </span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span
                              style={{
                                fontSize: '0.7rem',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                background: 'rgba(255, 255, 255, 0.08)',
                                fontWeight: 600,
                              }}
                            >
                              {r.permission.toUpperCase()}
                            </span>
                            <span className="mono" style={{ fontSize: '0.8rem' }}>
                              {r.resource}
                            </span>
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span className="mono" style={{ fontSize: '0.85rem', fontWeight: 700 }}>
                              {r.trust_score_after.toFixed(3)}
                            </span>
                            <span
                              style={{
                                fontSize: '0.7rem',
                                color: delta >= 0 ? 'var(--color-allow)' : 'var(--color-deny)',
                                fontWeight: 600,
                              }}
                            >
                              ({delta >= 0 ? '+' : ''}
                              {delta.toFixed(2)})
                            </span>
                          </div>
                        </td>
                        <td>
                          <span className={`badge badge-${r.decision}`}>
                            {getDecisionIcon(r.decision)}
                            {r.decision}
                          </span>
                        </td>
                        <td>
                          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                            {r.latency_ms.toFixed(1)}ms
                          </span>
                        </td>
                      </tr>

                      {/* Expandable Feature & SHAP Attribution Drawer */}
                      {isExpanded && (
                        <tr>
                          <td colSpan={8} style={{ padding: '16px 24px', background: 'rgba(15, 23, 42, 0.4)' }}>
                            <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px' }}>
                              {/* SHAP Visualization */}
                              <ShapExplainer
                                attributions={r.shap_attributions}
                                scoreBefore={r.trust_score_before}
                                scoreAfter={r.trust_score_after}
                              />

                              {/* Feature Vector & Details */}
                              <div
                                style={{
                                  background: 'rgba(15, 23, 42, 0.7)',
                                  padding: '16px',
                                  borderRadius: '10px',
                                  border: '1px solid var(--card-border)',
                                }}
                              >
                                <span
                                  style={{
                                    display: 'block',
                                    fontSize: '0.8rem',
                                    fontWeight: 600,
                                    color: 'var(--text-muted)',
                                    textTransform: 'uppercase',
                                    marginBottom: '10px',
                                  }}
                                >
                                  Dual-Stream Extracted Features
                                </span>
                                <div
                                  style={{
                                    display: 'grid',
                                    gridTemplateColumns: '1fr 1fr',
                                    gap: '8px',
                                    fontSize: '0.75rem',
                                  }}
                                >
                                  {Object.entries(r.features || {}).map(([k, v]) => (
                                    <div key={k} style={{ display: 'flex', justifyContent: 'space-between' }}>
                                      <span style={{ color: 'var(--text-dim)' }}>{k}:</span>
                                      <span className="mono" style={{ fontWeight: 600 }}>
                                        {typeof v === 'number' ? v.toFixed(2) : String(v)}
                                      </span>
                                    </div>
                                  ))}
                                </div>

                                {r.closed_loop_feedback && (
                                  <div
                                    style={{
                                      marginTop: '12px',
                                      padding: '8px 10px',
                                      borderRadius: '6px',
                                      background: 'var(--color-narrow-bg)',
                                      border: '1px solid rgba(245, 158, 11, 0.3)',
                                      fontSize: '0.75rem',
                                      color: 'var(--color-narrow)',
                                    }}
                                  >
                                    <strong>Closed-Loop Mutation:</strong> Wrote{' '}
                                    <span className="mono">{r.closed_loop_feedback.relation_tuple}</span> with TTL{' '}
                                    {r.closed_loop_feedback.ttl_seconds}s
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
