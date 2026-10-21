import React, { useState } from 'react';
import type { ClosedLoopRestriction } from '../types';
import { revokeRestriction } from '../api';
import { ShieldAlert, Trash2, Clock, CheckCircle } from 'lucide-react';

interface ClosedLoopViewerProps {
  restrictions: ClosedLoopRestriction[];
  onRefresh: () => void;
}

export const ClosedLoopViewer: React.FC<ClosedLoopViewerProps> = ({ restrictions, onRefresh }) => {
  const [revokingTuple, setRevokingTuple] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleRevoke = async (resource: string, subject: string, tuple: string) => {
    try {
      setRevokingTuple(tuple);
      await revokeRestriction(resource, subject);
      setMessage(`Successfully revoked restriction for ${subject} on ${resource}`);
      setTimeout(() => setMessage(null), 4000);
      onRefresh();
    } catch (err: any) {
      alert(`Failed to revoke restriction: ${err.message}`);
    } finally {
      setRevokingTuple(null);
    }
  };

  return (
    <div>
      <div
        className="glass-panel"
        style={{
          padding: '20px 24px',
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <div>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldAlert size={22} color="var(--color-narrow)" />
            Active Closed-Loop Narrowing Restrictions
          </h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '4px' }}>
            When a session trust score drops into <span style={{ color: 'var(--color-narrow)', fontWeight: 600 }}>[0.60, 0.85)</span>,
            the Decision Engine writes a dynamic <code className="mono">restricted_subject</code> relation to SpiceDB.
          </p>
        </div>
        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-narrow)', fontFamily: 'Outfit' }}>
            {restrictions.length}
          </span>
          <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            Active Tuples in SpiceDB
          </span>
        </div>
      </div>

      {message && (
        <div
          style={{
            background: 'var(--color-allow-bg)',
            border: '1px solid rgba(16, 185, 129, 0.4)',
            color: 'var(--color-allow)',
            padding: '12px 18px',
            borderRadius: '10px',
            marginBottom: '20px',
            fontSize: '0.875rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <CheckCircle size={16} />
          {message}
        </div>
      )}

      <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>SpiceDB Written Tuple</th>
                <th>Target Resource</th>
                <th>Restricted Subject</th>
                <th>Expires At</th>
                <th>TTL Remaining</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {restrictions.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '36px', color: 'var(--text-dim)' }}>
                    No active narrowing restrictions in SpiceDB. All active sessions have nominal trust.
                  </td>
                </tr>
              ) : (
                restrictions.map((item) => (
                  <tr key={item.tuple}>
                    <td>
                      <span className="mono" style={{ fontSize: '0.8rem', color: 'var(--color-narrow)' }}>
                        {item.tuple}
                      </span>
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: '0.8rem' }}>{item.resource}</span>
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: '0.8rem', fontWeight: 600 }}>{item.subject}</span>
                    </td>
                    <td>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {new Date(item.expires_at).toLocaleTimeString()}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '0.8rem',
                          color: 'var(--text-main)',
                        }}
                      >
                        <Clock size={13} color="var(--primary)" />
                        {Math.floor(item.ttl_remaining_seconds / 60)}m {item.ttl_remaining_seconds % 60}s
                      </span>
                    </td>
                    <td>
                      <button
                        onClick={() => handleRevoke(item.resource, item.subject, item.tuple)}
                        disabled={revokingTuple === item.tuple}
                        className="btn-danger"
                      >
                        <Trash2 size={13} />
                        {revokingTuple === item.tuple ? 'Revoking...' : 'Revoke'}
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
