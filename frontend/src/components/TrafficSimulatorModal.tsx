import React, { useState } from 'react';
import { sendSimulatedRequest } from '../api';
import { X, Play, Send } from 'lucide-react';

interface TrafficSimulatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRefreshDashboard: () => void;
}

export const TrafficSimulatorModal: React.FC<TrafficSimulatorModalProps> = ({
  isOpen,
  onClose,
  onRefreshDashboard,
}) => {
  const [subject, setSubject] = useState('user:alice');
  const [sessionId, setSessionId] = useState('sess_sim_001');
  const [path, setPath] = useState('/api/v1/documents/doc_1');
  const [method, setMethod] = useState('GET');
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<any | null>(null);

  if (!isOpen) return null;

  const presets = [
    {
      name: 'Benign User (Alice)',
      subject: 'user:alice',
      sessionId: 'sess_alice_norm',
      path: '/api/v1/documents/doc_1',
      method: 'GET',
      badge: 'allow',
      desc: 'Nominal traffic pattern. High trust score ≥ 0.85.',
    },
    {
      name: 'Privilege Shortcut Attempt',
      subject: 'user:charlie',
      sessionId: 'sess_charlie_novel',
      path: '/api/v1/documents/doc_confidential',
      method: 'GET',
      badge: 'narrow',
      desc: 'Novel path structure. Triggers NARROW [0.60, 0.85) and SpiceDB write-back.',
    },
    {
      name: 'Rate Burst / MFA Challenge',
      subject: 'user:bob',
      sessionId: 'sess_bob_burst',
      path: '/api/v1/documents/doc_1',
      method: 'POST',
      badge: 'step_up',
      desc: 'High request frequency. Triggers STEP-UP challenge [0.40, 0.60).',
    },
    {
      name: 'Critical Anomaly / Attack',
      subject: 'user:attacker',
      sessionId: 'sess_attacker_999',
      path: '/api/v1/documents/doc_classified',
      method: 'DELETE',
      badge: 'deny',
      desc: 'Multi-feature deviation. Triggers DENY < 0.40.',
    },
  ];

  const handleApplyPreset = (p: typeof presets[0]) => {
    setSubject(p.subject);
    setSessionId(p.sessionId);
    setPath(p.path);
    setMethod(p.method);
    setResponse(null);
  };

  const handleSend = async () => {
    setLoading(true);
    setResponse(null);
    try {
      const res = await sendSimulatedRequest({
        path,
        method,
        subject,
        sessionId,
      });
      setResponse(res);
      onRefreshDashboard();
    } catch (err: any) {
      setResponse({
        status: 500,
        headers: {},
        data: { error: err.message || 'Request failed to reach Data Plane' },
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '20px',
      }}
    >
      <div
        className="glass-panel"
        style={{
          width: '100%',
          maxWidth: '750px',
          maxHeight: '90vh',
          overflowY: 'auto',
          padding: '28px',
          background: 'rgba(15, 23, 42, 0.95)',
          border: '1px solid rgba(99, 102, 241, 0.3)',
          boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Play size={20} color="var(--primary)" />
              Live Traffic & Anomaly Simulator
            </h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '2px' }}>
              Inject requests into Data Plane (:3003) to trigger live trust decay, scoring, and closed-loop actions.
            </p>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer' }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Presets Grid */}
        <div style={{ marginBottom: '20px' }}>
          <span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase' }}>
            Select Attack / Behavior Profile
          </span>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
            {presets.map((p) => (
              <div
                key={p.name}
                onClick={() => handleApplyPreset(p)}
                style={{
                  padding: '12px',
                  borderRadius: '8px',
                  background: 'rgba(30, 41, 59, 0.5)',
                  border: '1px solid var(--card-border)',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--primary)')}
                onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--card-border)')}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{p.name}</span>
                  <span className={`badge badge-${p.badge}`} style={{ fontSize: '0.65rem', padding: '2px 6px' }}>
                    {p.badge}
                  </span>
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', margin: 0 }}>{p.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Form Controls */}
        <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '12px', marginBottom: '14px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Method</label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid var(--card-border)',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
              }}
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Request Path</label>
            <input
              type="text"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              className="mono"
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid var(--card-border)',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
              }}
            />
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '20px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Subject Principal (X-Subject)</label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="mono"
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid var(--card-border)',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
              }}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>Session ID (X-Session-ID)</label>
            <input
              type="text"
              value={sessionId}
              onChange={(e) => setSessionId(e.target.value)}
              className="mono"
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                background: 'rgba(15, 23, 42, 0.8)',
                border: '1px solid var(--card-border)',
                color: 'var(--text-main)',
                fontSize: '0.85rem',
              }}
            />
          </div>
        </div>

        {/* Action Button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '20px' }}>
          <button onClick={handleSend} disabled={loading} className="btn-primary" style={{ padding: '10px 24px' }}>
            <Send size={15} />
            {loading ? 'Evaluating via Data Plane...' : 'Send Request'}
          </button>
        </div>

        {/* Response Box */}
        {response && (
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.9)',
              padding: '16px',
              borderRadius: '8px',
              border: '1px solid var(--card-border)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>HTTP Status:</span>
                <span
                  style={{
                    fontWeight: 700,
                    color: response.status === 200 ? 'var(--color-allow)' : response.status === 401 ? 'var(--color-step-up)' : 'var(--color-deny)',
                  }}
                >
                  {response.status}
                </span>
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                {response.headers['x-trust-decision'] && (
                  <span className={`badge badge-${response.headers['x-trust-decision']}`}>
                    {response.headers['x-trust-decision']}
                  </span>
                )}
                {response.headers['x-trust-narrowed'] && (
                  <span className="badge badge-narrow">CLOSED-LOOP NARROWED</span>
                )}
              </div>
            </div>

            {response.headers['x-trust-score'] && (
              <div style={{ fontSize: '0.8rem', color: 'var(--text-main)', marginBottom: '8px' }}>
                Calculated Trust Score: <strong className="mono">{response.headers['x-trust-score']}</strong>
              </div>
            )}

            <pre
              className="mono"
              style={{
                fontSize: '0.75rem',
                color: '#cbd5e1',
                maxHeight: '160px',
                overflowY: 'auto',
                background: 'rgba(0, 0, 0, 0.4)',
                padding: '10px',
                borderRadius: '6px',
              }}
            >
              {typeof response.data === 'object' ? JSON.stringify(response.data, null, 2) : response.data}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};
