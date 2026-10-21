import { useState } from 'react';
import { Shield, RotateCcw } from 'lucide-react';
import { SubjectId, SimulatorUser, RequestRecord } from './types';
import { UserSwitcher } from './components/UserSwitcher';
import { ActionPanel } from './components/ActionPanel';
import { ResponseViewer } from './components/ResponseViewer';
import { StepUpModal } from './components/StepUpModal';

const USERS: SimulatorUser[] = [
  { id: 'user:alice', name: 'Alice Vance', role: 'Engineering Lead', department: 'Engineering', avatarColor: '#06b6d4', initials: 'AV' },
  { id: 'user:bob', name: 'Bob Stone', role: 'Marketing Director', department: 'Marketing', avatarColor: '#8b5cf6', initials: 'BS' },
  { id: 'user:charlie', name: 'Charlie King', role: 'Executive Administrator', department: 'Executive', avatarColor: '#f59e0b', initials: 'CK' },
  { id: 'user:darth', name: 'Darth Vane', role: 'External Adversary', department: 'Outside Organization', avatarColor: '#ef4444', initials: 'DV' },
];

export default function App() {
  const [currentUser, setCurrentUser] = useState<SubjectId>('user:alice');
  const [latestRequest, setLatestRequest] = useState<RequestRecord | null>(null);
  const [history, setHistory] = useState<RequestRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [showStepUpModal, setShowStepUpModal] = useState(false);


  const executeRequest = async ({
    method,
    endpoint,
    headers = {},
    body,
    label: _label,
  }: {
    method: string;
    endpoint: string;
    headers?: Record<string, string>;
    body?: any;
    label: string;
  }) => {
    setIsLoading(true);
    const start = performance.now();
    const targetUrl = `http://localhost:3003${endpoint}`;

    try {
      const res = await fetch(targetUrl, {
        method,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${currentUser}`,
          'X-Subject': currentUser,
          'X-Session-ID': `sess_${currentUser.replace(':', '_')}`,
          ...headers,
        },

        body: body ? JSON.stringify(body) : undefined,
      });

      const latencyMs = performance.now() - start;
      const text = await res.text();

      // Extract Zero-Trust response headers if supplied by gateway
      const trustScoreHeader = res.headers.get('x-trust-score');
      const trustBandHeader = res.headers.get('x-trust-band');
      const parsedTrustScore = trustScoreHeader ? parseFloat(trustScoreHeader) : undefined;

      // Determine decision action
      let decision: RequestRecord['decision'] = 'allow';
      if (trustBandHeader === 'step_up' || (res.status === 403 && text.includes('step_up'))) {
        decision = 'step_up';
      } else if (trustBandHeader === 'narrow' || text.includes('narrow')) {
        decision = 'narrow';
      } else if (!res.ok) {
        decision = res.status === 403 ? 'deny' : 'deny';
      }

      // Check if Step-Up modal should be triggered

      if (decision === 'step_up' || (res.status === 403 && text.toLowerCase().includes('step_up'))) {
        setShowStepUpModal(true);
      }

      let prettyResponse = text;
      try {
        prettyResponse = JSON.stringify(JSON.parse(text), null, 2);
      } catch {
        // Keep raw text
      }

      const record: RequestRecord = {
        id: Math.random().toString(36).substring(7),
        timestamp: new Date().toLocaleTimeString(),
        user: currentUser,
        method,
        endpoint,
        clientIp: headers['X-Forwarded-For'] || '127.0.0.1 (Localhost)',
        status: res.status,
        decision,
        trustScore: parsedTrustScore,
        latencyMs,
        responseBody: prettyResponse,
      };

      setLatestRequest(record);
      setHistory((prev) => [record, ...prev.slice(0, 49)]);
    } catch (err: any) {
      const latencyMs = performance.now() - start;
      const record: RequestRecord = {
        id: Math.random().toString(36).substring(7),
        timestamp: new Date().toLocaleTimeString(),
        user: currentUser,
        method,
        endpoint,
        clientIp: headers['X-Forwarded-For'] || '127.0.0.1',
        status: 502,
        decision: 'deny',
        latencyMs,
        responseBody: JSON.stringify({ error: 'Gateway Unreachable', message: err.message }, null, 2),
      };
      setLatestRequest(record);
      setHistory((prev) => [record, ...prev.slice(0, 49)]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetDemo = async () => {
    try {
      setIsLoading(true);
      // 1. Reset backend in-memory state
      await fetch('http://localhost:4013/api/v1/admin/reset-demo', { method: 'POST' }).catch(() => {});

      // 2. Clear all audit logs and reset all user trust scores on Control Plane
      await fetch('http://localhost:3002/api/v1/users/reset-all', { method: 'POST' }).catch(() => {});

      setLatestRequest(null);
      setHistory([]);

    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Header */}
      <header style={{
        background: 'rgba(13, 18, 29, 0.8)',
        backdropFilter: 'blur(12px)',
        borderBottom: '1px solid var(--border-subtle)',
        padding: '16px 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 40
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)',
            borderRadius: '10px',
            padding: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 16px rgba(6, 182, 212, 0.4)'
          }}>
            <Shield size={24} color="#ffffff" />
          </div>
          <div>
            <h1 style={{ fontSize: '18px', fontWeight: 700, letterSpacing: '-0.02em', color: '#fff' }}>
              Zero-Trust API Gateway Simulator
            </h1>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Evaluation Testbed for Graph-Aware Dynamic Authorization & Anomaly Detection
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-subtle)',
            borderRadius: '6px',
            padding: '4px 10px',
            fontFamily: 'var(--font-mono)',
            fontSize: '12px',
            color: 'var(--color-cyan)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#10b981' }}></span>
            Proxy Target: http://localhost:3003
          </div>

          <button
            onClick={handleResetDemo}
            disabled={isLoading}
            style={{
              background: 'var(--bg-secondary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '6px 12px',
              fontSize: '12px',
              fontWeight: 600,
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <RotateCcw size={14} /> Reset Demo State
          </button>
        </div>
      </header>

      {/* Main Content Body */}
      <main style={{ padding: '24px', flex: 1, display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* Active Subject Switcher */}
        <UserSwitcher
          users={USERS}
          currentUser={currentUser}
          onSelectUser={setCurrentUser}
        />

        {/* Action Panel & Attack Scenarios */}
        <ActionPanel
          currentUser={currentUser}
          onExecuteRequest={executeRequest}
          isLoading={isLoading}
        />

        {/* Gateway Response Inspector */}
        <ResponseViewer
          latestRequest={latestRequest}
          history={history}
          onClearHistory={() => setHistory([])}
        />
      </main>

      {/* Step-Up MFA Challenge Modal */}
      <StepUpModal
        isOpen={showStepUpModal}
        onClose={() => setShowStepUpModal(false)}
        currentUser={currentUser}
        onSuccess={() => {
          setShowStepUpModal(false);
        }}
      />

    </div>
  );
}
