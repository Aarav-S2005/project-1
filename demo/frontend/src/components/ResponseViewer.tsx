import { Terminal, Clock, CheckCircle2, AlertCircle, ShieldAlert } from 'lucide-react';
import { RequestRecord } from '../types';

interface ResponseViewerProps {
  latestRequest: RequestRecord | null;
  history: RequestRecord[];
  onClearHistory: () => void;
}

export function ResponseViewer({ latestRequest, history, onClearHistory }: ResponseViewerProps) {
  const getDecisionBadge = (decision: RequestRecord['decision']) => {
    switch (decision) {
      case 'allow':
        return { text: 'ALLOW', color: 'var(--color-allow)', bg: 'var(--color-allow-bg)', icon: CheckCircle2 };
      case 'step_up':
        return { text: 'STEP-UP CHALLENGE', color: 'var(--color-step-up)', bg: 'var(--color-step-up-bg)', icon: AlertCircle };
      case 'narrow':
        return { text: 'NARROW (CLOSED-LOOP)', color: 'var(--color-narrow)', bg: 'var(--color-narrow-bg)', icon: ShieldAlert };
      case 'deny':
      default:
        return { text: 'DENY (REBAC)', color: 'var(--color-deny)', bg: 'var(--color-deny-bg)', icon: ShieldAlert };
    }
  };

  return (
    <section className="glass-panel" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Terminal size={18} color="var(--color-cyan)" />
          <h2 style={{ fontSize: '15px', fontWeight: 600 }}>Live Gateway Evaluation & Response Inspector</h2>
        </div>
        {history.length > 0 && (
          <button
            onClick={onClearHistory}
            style={{
              background: 'transparent',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
              fontSize: '11px',
              padding: '4px 8px',
              borderRadius: '4px',
            }}
          >
            Clear History
          </button>
        )}
      </div>

      {!latestRequest ? (
        <div style={{
          padding: '36px',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: '13px',
          border: '1px dashed var(--border-subtle)',
          borderRadius: '12px'
        }}>
          No requests recorded yet. Select an identity and click any operation or attack scenario above to observe live Zero-Trust gateway evaluation.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Header Metric Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px' }}>
            {/* Decision */}
            {(() => {
              const badge = getDecisionBadge(latestRequest.decision);
              const Icon = badge.icon;
              return (
                <div style={{
                  background: 'var(--bg-secondary)',
                  border: `1px solid ${badge.color}`,
                  borderRadius: '10px',
                  padding: '12px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px'
                }}>
                  <Icon size={22} color={badge.color} />
                  <div>
                    <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Decision</div>
                    <div style={{ fontSize: '12px', fontWeight: 700, color: badge.color }}>{badge.text}</div>
                  </div>
                </div>
              );
            })()}

            {/* HTTP Status */}
            <div style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '10px',
              padding: '12px',
            }}>
              <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>HTTP Status</div>
              <div style={{
                fontSize: '16px',
                fontWeight: 700,
                color: latestRequest.status < 300 ? 'var(--color-allow)' : latestRequest.status < 500 ? 'var(--color-step-up)' : 'var(--color-deny)'
              }}>
                {latestRequest.status} {latestRequest.status === 200 ? 'OK' : latestRequest.status === 403 ? 'Forbidden' : ''}
              </div>
            </div>

            {/* Target Microservice */}
            <div style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '10px',
              padding: '12px',
            }}>
              <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Target Service</div>
              <div style={{ fontSize: '14px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-cyan)' }}>
                {latestRequest.endpoint.split('/')[3]?.toUpperCase() || 'GATEWAY'}
              </div>
            </div>

            {/* Latency */}
            <div style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '10px',
              padding: '12px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px'
            }}>
              <Clock size={20} color="var(--color-cyan)" />
              <div>
                <div style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-muted)', fontWeight: 600 }}>Evaluation Latency</div>
                <div style={{ fontSize: '16px', fontWeight: 700, fontFamily: 'var(--font-mono)', color: 'var(--color-cyan)' }}>
                  {latestRequest.latencyMs.toFixed(1)} ms
                </div>
              </div>
            </div>
          </div>

          {/* Request Signature details */}
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '8px',
            padding: '10px 14px',
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            gap: '16px',
            fontSize: '12px',
            fontFamily: 'var(--font-mono)',
          }}>
            <div><span style={{ color: 'var(--text-muted)' }}>Method:</span> <strong style={{ color: '#fff' }}>{latestRequest.method}</strong></div>
            <div><span style={{ color: 'var(--text-muted)' }}>Target:</span> <strong style={{ color: 'var(--color-cyan)' }}>{latestRequest.endpoint}</strong></div>
            <div><span style={{ color: 'var(--text-muted)' }}>Client IP:</span> <strong style={{ color: '#fff' }}>{latestRequest.clientIp}</strong></div>
            <div><span style={{ color: 'var(--text-muted)' }}>Subject:</span> <strong style={{ color: '#fff' }}>{latestRequest.user}</strong></div>
          </div>

          {/* Response payload viewer */}
          <div style={{
            background: '#090d16',
            border: '1px solid var(--border-subtle)',
            borderRadius: '8px',
            padding: '14px',
            maxHeight: '260px',
            overflowY: 'auto',
          }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', fontWeight: 600 }}>
              Response Payload
            </div>
            <pre style={{
              margin: 0,
              fontSize: '12px',
              fontFamily: 'var(--font-mono)',
              color: '#38bdf8',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all'
            }}>
              {latestRequest.responseBody}
            </pre>
          </div>
        </div>
      )}
    </section>
  );
}
