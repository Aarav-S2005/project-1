import { useState } from 'react';
import {
  Send,
  Zap,
  Globe,
  FileSearch,
  AlertTriangle,
  ShieldAlert,
  Skull,
  ShieldX,
  Terminal,
} from 'lucide-react';

import { SubjectId } from '../types';

interface ActionPanelProps {
  currentUser: SubjectId;
  onExecuteRequest: (params: {
    method: string;
    endpoint: string;
    headers?: Record<string, string>;
    body?: any;
    label: string;
  }) => Promise<void>;
  isLoading: boolean;
}

export function ActionPanel({ currentUser, onExecuteRequest, isLoading }: ActionPanelProps) {
  const [burstProgress, setBurstProgress] = useState<number | null>(null);

  const isDarth = currentUser === 'user:darth';

  // Geo-Velocity / Location Jump attack simulation
  const handleGeoVelocityAttack = async () => {
    if (isDarth) {
      // Darth jumps through Tor exit nodes
      await onExecuteRequest({
        method: 'GET',
        endpoint: '/api/v1/documents/doc_exec_confidential',
        headers: { 'X-Forwarded-For': '185.220.101.5' }, // Amsterdam Tor Exit Node
        label: 'Tor Exit Hop #1 (Amsterdam IP: 185.220.101.5)',
      });

      setTimeout(async () => {
        await onExecuteRequest({
          method: 'GET',
          endpoint: '/api/v1/documents/doc_exec_confidential',
          headers: { 'X-Forwarded-For': '95.173.136.1' }, // St. Petersburg IP
          label: 'Tor Exit Hop #2 (St. Petersburg IP: 95.173.136.1)',
        });
      }, 400);
      return;
    }

    const ip1 =
      currentUser === 'user:alice'
        ? '133.242.0.1'
        : currentUser === 'user:bob'
        ? '1.120.0.1'
        : '198.51.100.1';
    const ip2 =
      currentUser === 'user:alice'
        ? '212.58.244.70'
        : currentUser === 'user:bob'
        ? '194.25.0.1'
        : '103.28.0.1';
    const loc1 =
      currentUser === 'user:alice' ? 'Tokyo' : currentUser === 'user:bob' ? 'Sydney' : 'New York';
    const loc2 =
      currentUser === 'user:alice' ? 'London' : currentUser === 'user:bob' ? 'Frankfurt' : 'Singapore';
    const targetDoc =
      currentUser === 'user:alice'
        ? '/api/v1/documents/doc_eng_specs'
        : currentUser === 'user:bob'
        ? '/api/v1/documents/doc_mkt_campaign'
        : '/api/v1/documents/doc_roadmap';

    await onExecuteRequest({
      method: 'GET',
      endpoint: targetDoc,
      headers: { 'X-Forwarded-For': ip1 },
      label: `Location Jump #1 (${loc1} IP: ${ip1})`,
    });

    setTimeout(async () => {
      await onExecuteRequest({
        method: 'GET',
        endpoint: targetDoc,
        headers: { 'X-Forwarded-For': ip2 },
        label: `Location Jump #2 (${loc2} IP: ${ip2})`,
      });
    }, 400);
  };

  // High-frequency burst attack simulation
  const handleBurstAttack = async () => {
    setBurstProgress(0);
    const count = isDarth ? 20 : 15;
    const endpoint = isDarth
      ? '/api/v1/documents/doc_exec_confidential'
      : currentUser === 'user:alice'
      ? '/api/v1/documents/doc_eng_specs'
      : currentUser === 'user:bob'
      ? '/api/v1/documents/doc_mkt_campaign'
      : '/api/v1/documents/doc_roadmap';

    for (let i = 1; i <= count; i++) {
      setBurstProgress(i);
      await onExecuteRequest({
        method: 'GET',
        endpoint,
        label: isDarth
          ? `Credential Stuffing & Burst Flood [${i}/${count}]`
          : `Burst Flood [${i}/${count}]`,
      });
      await new Promise((r) => setTimeout(r, 50));
    }
    setBurstProgress(null);
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
      {/* Normal Business Operations / Adversary Probe Section */}
      <section className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          {isDarth ? (
            <Skull size={18} color="var(--color-deny)" />
          ) : (
            <Send size={18} color="var(--color-allow)" />
          )}
          <h2 style={{ fontSize: '15px', fontWeight: 600 }}>
            {isDarth ? 'Untrusted Business Requests (External Adversary)' : 'Legitimate Business Requests'}
          </h2>
        </div>

        {isDarth ? (
          <div
            style={{
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              padding: '12px 14px',
              marginBottom: '16px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f87171', fontWeight: 600, fontSize: '12px', marginBottom: '4px' }}>
              <ShieldX size={15} />
              Zero-Trust Policy Enforcement
            </div>
            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.5 }}>
              Darth is an <strong>external attacker</strong> with no organization membership or ReBAC relationships in SpiceDB. Standard API operations will fail continuous authorization checks.
            </p>
          </div>
        ) : (
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Authorized operations mapped through Gateway Data Plane (<code className="font-mono">:3003</code>) to demo microservices.
          </p>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {isDarth ? (
            <>
              <button
                disabled={isLoading}
                onClick={() =>
                  onExecuteRequest({
                    method: 'GET',
                    endpoint: '/api/v1/users/me',
                    label: 'Darth Probing Identity Directory',
                  })
                }
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  color: '#fff',
                }}
              >
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Probe User Directory Profile (:4010)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    GET /api/v1/users/me
                  </div>
                </div>
                <span
                  style={{
                    fontSize: '11px',
                    color: 'var(--color-deny)',
                    background: 'var(--color-deny-bg)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                  }}
                >
                  Unauthenticated
                </span>
              </button>

              <button
                disabled={isLoading}
                onClick={() =>
                  onExecuteRequest({
                    method: 'GET',
                    endpoint: '/api/v1/documents/doc_eng_specs',
                    label: 'Darth Probing Engineering Blueprints',
                  })
                }
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  color: '#fff',
                }}
              >
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Probe Engineering Document (:4011)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    GET /api/v1/documents/doc_eng_specs
                  </div>
                </div>
                <span
                  style={{
                    fontSize: '11px',
                    color: 'var(--color-deny)',
                    background: 'var(--color-deny-bg)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                  }}
                >
                  ReBAC Denied
                </span>
              </button>

              <button
                disabled={isLoading}
                onClick={() =>
                  onExecuteRequest({
                    method: 'GET',
                    endpoint: '/api/v1/payroll/pay_alice',
                    label: 'Darth Probing Payroll Vault',
                  })
                }
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  color: '#fff',
                }}
              >
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Probe Payroll Vault (:4012)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    GET /api/v1/payroll/pay_alice
                  </div>
                </div>
                <span
                  style={{
                    fontSize: '11px',
                    color: 'var(--color-deny)',
                    background: 'var(--color-deny-bg)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                  }}
                >
                  ReBAC Denied
                </span>
              </button>

              <button
                disabled={isLoading}
                onClick={() =>
                  onExecuteRequest({
                    method: 'GET',
                    endpoint: '/api/v1/admin/health',
                    label: 'Darth Scanning Internal Admin Endpoints',
                  })
                }
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  color: '#fff',
                }}
              >
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Probe Admin Gateway Health (:4013)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    GET /api/v1/admin/health
                  </div>
                </div>
                <span
                  style={{
                    fontSize: '11px',
                    color: 'var(--color-deny)',
                    background: 'var(--color-deny-bg)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                  }}
                >
                  Forbidden
                </span>
              </button>
            </>
          ) : (
            <>
              <button
                disabled={isLoading}
                onClick={() =>
                  onExecuteRequest({
                    method: 'GET',
                    endpoint: '/api/v1/users/me',
                    label: 'View Own Identity Profile',
                  })
                }
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  color: '#fff',
                }}
              >
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Get Profile (:4010)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    GET /api/v1/users/me
                  </div>
                </div>
                <span
                  style={{
                    fontSize: '11px',
                    color: 'var(--color-allow)',
                    background: 'var(--color-allow-bg)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                  }}
                >
                  Allow
                </span>
              </button>

              <button
                disabled={isLoading}
                onClick={() =>
                  onExecuteRequest({
                    method: 'GET',
                    endpoint:
                      currentUser === 'user:alice'
                        ? '/api/v1/documents/doc_eng_specs'
                        : currentUser === 'user:bob'
                        ? '/api/v1/documents/doc_mkt_campaign'
                        : '/api/v1/documents/doc_roadmap',
                    label: 'View Authorized Department Spec',
                  })
                }
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  color: '#fff',
                }}
              >
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Access Department Document (:4011)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    GET /api/v1/documents/
                    {currentUser === 'user:alice'
                      ? 'doc_eng_specs'
                      : currentUser === 'user:bob'
                      ? 'doc_mkt_campaign'
                      : 'doc_roadmap'}
                  </div>
                </div>
                <span
                  style={{
                    fontSize: '11px',
                    color: 'var(--color-allow)',
                    background: 'var(--color-allow-bg)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                  }}
                >
                  ReBAC Owner/Editor
                </span>
              </button>

              <button
                disabled={isLoading}
                onClick={() =>
                  onExecuteRequest({
                    method: 'GET',
                    endpoint: '/api/v1/documents/doc_roadmap',
                    label: 'View Company Strategic Roadmap',
                  })
                }
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  color: '#fff',
                }}
              >
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Access Shared Roadmap (:4011)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    GET /api/v1/documents/doc_roadmap
                  </div>
                </div>
                <span
                  style={{
                    fontSize: '11px',
                    color: 'var(--color-allow)',
                    background: 'var(--color-allow-bg)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                  }}
                >
                  ReBAC Viewer
                </span>
              </button>

              <button
                disabled={isLoading}
                onClick={() =>
                  onExecuteRequest({
                    method: 'GET',
                    endpoint:
                      currentUser === 'user:alice'
                        ? '/api/v1/payroll/pay_alice'
                        : currentUser === 'user:bob'
                        ? '/api/v1/payroll/pay_bob'
                        : '/api/v1/payroll/pay_exec',
                    label: 'View Own Payroll Records',
                  })
                }
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  color: '#fff',
                }}
              >
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Access Own Payroll (:4012)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    GET /api/v1/payroll/
                    {currentUser === 'user:alice'
                      ? 'pay_alice'
                      : currentUser === 'user:bob'
                      ? 'pay_bob'
                      : 'pay_exec'}
                  </div>
                </div>
                <span
                  style={{
                    fontSize: '11px',
                    color: 'var(--color-allow)',
                    background: 'var(--color-allow-bg)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                  }}
                >
                  Personal Record
                </span>
              </button>
            </>
          )}
        </div>
      </section>

      {/* Attack Scenarios & Anomaly Triggering */}
      <section className="glass-panel" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <ShieldAlert size={18} color="var(--color-deny)" />
          <h2 style={{ fontSize: '15px', fontWeight: 600 }}>
            {isDarth ? 'Darth Adversary Attack Arsenal' : 'Zero-Trust Anomaly & Attack Scenarios'}
          </h2>
        </div>
        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
          {isDarth
            ? 'Adversarial attack vectors executing from outside the perimeter to test Gateway ML & ReBAC resilience.'
            : 'Live attack vectors that trigger trust decay, Isolation Forest anomalies, and ReBAC policy checks.'}
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {/* Persona-specific Scenario 1: Location Jump */}
          <button
            disabled={isLoading}
            onClick={handleGeoVelocityAttack}
            style={{
              background: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              padding: '10px 14px',
              textAlign: 'left',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              color: '#fff',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Globe size={18} color={isDarth ? 'var(--color-deny)' : 'var(--color-step-up)'} />
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600 }}>
                  {isDarth ? 'Tor Exit Node Geo-Velocity Hop' : 'Location Jump (Geo-Velocity)'}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  {isDarth
                    ? 'Amsterdam Tor (185.220.101.5) ➔ St. Petersburg (95.173.136.1)'
                    : currentUser === 'user:alice'
                    ? 'Tokyo (133.242.0.1) ➔ London (212.58.244.70)'
                    : currentUser === 'user:bob'
                    ? 'Sydney (1.120.0.1) ➔ Frankfurt (194.25.0.1)'
                    : 'New York (198.51.100.1) ➔ Singapore (103.28.0.1)'}
                </div>
              </div>
            </div>
            <span
              style={{
                fontSize: '11px',
                color: isDarth ? 'var(--color-deny)' : 'var(--color-step-up)',
                background: isDarth ? 'var(--color-deny-bg)' : 'var(--color-step-up-bg)',
                padding: '2px 8px',
                borderRadius: '4px',
              }}
            >
              {isDarth ? 'Tor Anomaly' : 'Triggers Step-Up'}
            </span>
          </button>

          {/* Persona-specific Scenario 2: Burst Attack */}
          <button
            disabled={isLoading || burstProgress !== null}
            onClick={handleBurstAttack}
            style={{
              background: 'rgba(245, 158, 11, 0.08)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              borderRadius: '8px',
              padding: '10px 14px',
              textAlign: 'left',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              color: '#fff',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Zap size={18} color="var(--color-step-up)" />
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600 }}>
                  {isDarth ? 'DDoS & Credential Stuffing Burst' : 'High-Frequency Request Burst'}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  {burstProgress !== null
                    ? `Blasting request ${burstProgress}/${isDarth ? 20 : 15}...`
                    : isDarth
                    ? '20 rapid brute-force requests blasting gateway'
                    : currentUser === 'user:alice'
                    ? '15 automated script scrapes in 1.5s'
                    : currentUser === 'user:bob'
                    ? '15 rapid queries downloading collateral'
                    : '15 parallel bulk exfiltration queries'}
                </div>
              </div>
            </div>
            <span
              style={{
                fontSize: '11px',
                color: 'var(--color-step-up)',
                background: 'var(--color-step-up-bg)',
                padding: '2px 8px',
                borderRadius: '4px',
              }}
            >
              Rate Anomaly
            </span>
          </button>

          {/* Persona-specific Scenario 3: Cross-Department / Unauthorized Peeking / Reconnaissance */}
          {currentUser === 'user:alice' && (
            <button
              disabled={isLoading}
              onClick={() =>
                onExecuteRequest({
                  method: 'GET',
                  endpoint: '/api/v1/documents/doc_mkt_campaign',
                  label: 'Alice Accessing Marketing Campaign',
                })
              }
              style={{
                background: 'rgba(236, 72, 153, 0.08)',
                border: '1px solid rgba(236, 72, 153, 0.3)',
                borderRadius: '8px',
                padding: '10px 14px',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                color: '#fff',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileSearch size={18} color="var(--color-narrow)" />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Cross-Department Peeking (Marketing)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    GET /api/v1/documents/doc_mkt_campaign
                  </div>
                </div>
              </div>
              <span
                style={{
                  fontSize: '11px',
                  color: 'var(--color-deny)',
                  background: 'var(--color-deny-bg)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                }}
              >
                ReBAC Deny
              </span>
            </button>
          )}

          {currentUser === 'user:bob' && (
            <button
              disabled={isLoading}
              onClick={() =>
                onExecuteRequest({
                  method: 'GET',
                  endpoint: '/api/v1/documents/doc_eng_specs',
                  label: 'Bob Accessing Engineering Specs',
                })
              }
              style={{
                background: 'rgba(236, 72, 153, 0.08)',
                border: '1px solid rgba(236, 72, 153, 0.3)',
                borderRadius: '8px',
                padding: '10px 14px',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                color: '#fff',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileSearch size={18} color="var(--color-narrow)" />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Cross-Department Peeking (Engineering)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    GET /api/v1/documents/doc_eng_specs
                  </div>
                </div>
              </div>
              <span
                style={{
                  fontSize: '11px',
                  color: 'var(--color-deny)',
                  background: 'var(--color-deny-bg)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                }}
              >
                ReBAC Deny
              </span>
            </button>
          )}

          {currentUser === 'user:charlie' && (
            <button
              disabled={isLoading}
              onClick={() =>
                onExecuteRequest({
                  method: 'DELETE',
                  endpoint: '/api/v1/documents/doc_eng_specs',
                  label: 'Charlie Deleting Engineering Specs',
                })
              }
              style={{
                background: 'rgba(236, 72, 153, 0.08)',
                border: '1px solid rgba(236, 72, 153, 0.3)',
                borderRadius: '8px',
                padding: '10px 14px',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                color: '#fff',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileSearch size={18} color="var(--color-narrow)" />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Unauthorized Mutation (Delete Specs)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    DELETE /api/v1/documents/doc_eng_specs
                  </div>
                </div>
              </div>
              <span
                style={{
                  fontSize: '11px',
                  color: 'var(--color-deny)',
                  background: 'var(--color-deny-bg)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                }}
              >
                ReBAC Deny
              </span>
            </button>
          )}

          {isDarth && (
            <button
              disabled={isLoading}
              onClick={() =>
                onExecuteRequest({
                  method: 'GET',
                  endpoint: '/api/v1/documents/doc_exec_confidential',
                  label: 'Darth Scanning Executive Confidential Files',
                })
              }
              style={{
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '8px',
                padding: '10px 14px',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                color: '#fff',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <FileSearch size={18} color="var(--color-deny)" />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Targeted Reconnaissance (Confidential M&A)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    GET /api/v1/documents/doc_exec_confidential
                  </div>
                </div>
              </div>
              <span
                style={{
                  fontSize: '11px',
                  color: 'var(--color-deny)',
                  background: 'var(--color-deny-bg)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                }}
              >
                Blocked
              </span>
            </button>
          )}

          {/* Persona-specific Scenario 4: Privilege Escalation / Exploits */}
          {currentUser === 'user:alice' && (
            <button
              disabled={isLoading}
              onClick={() =>
                onExecuteRequest({
                  method: 'POST',
                  endpoint: '/api/v1/admin/purge-cache',
                  label: 'Alice Privilege Escalation (Purge Cache)',
                })
              }
              style={{
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '8px',
                padding: '10px 14px',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                color: '#fff',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <AlertTriangle size={18} color="var(--color-deny)" />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Privilege Escalation (Purge Cache)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    POST /api/v1/admin/purge-cache
                  </div>
                </div>
              </div>
              <span
                style={{
                  fontSize: '11px',
                  color: 'var(--color-deny)',
                  background: 'var(--color-deny-bg)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                }}
              >
                Denied / Narrow
              </span>
            </button>
          )}

          {currentUser === 'user:bob' && (
            <button
              disabled={isLoading}
              onClick={() =>
                onExecuteRequest({
                  method: 'GET',
                  endpoint: '/api/v1/documents/doc_exec_confidential',
                  label: 'Bob Accessing Confidential M&A',
                })
              }
              style={{
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '8px',
                padding: '10px 14px',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                color: '#fff',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <AlertTriangle size={18} color="var(--color-deny)" />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Access Executive M&A Records</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    GET /api/v1/documents/doc_exec_confidential
                  </div>
                </div>
              </div>
              <span
                style={{
                  fontSize: '11px',
                  color: 'var(--color-deny)',
                  background: 'var(--color-deny-bg)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                }}
              >
                Denied / Narrow
              </span>
            </button>
          )}

          {currentUser === 'user:charlie' && (
            <button
              disabled={isLoading}
              onClick={() =>
                onExecuteRequest({
                  method: 'GET',
                  endpoint: '/api/v1/payroll/pay_alice',
                  headers: { 'X-TLS-Fingerprint': 'spoofed_tls_fp_9999' },
                  label: 'Charlie with Suspicious TLS Fingerprint',
                })
              }
              style={{
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '8px',
                padding: '10px 14px',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                color: '#fff',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <AlertTriangle size={18} color="var(--color-deny)" />
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>Fingerprint Anomaly (Spoofed Client)</div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                    TLS Mismatch on Executive Access
                  </div>
                </div>
              </div>
              <span
                style={{
                  fontSize: '11px',
                  color: 'var(--color-step-up)',
                  background: 'var(--color-step-up-bg)',
                  padding: '2px 8px',
                  borderRadius: '4px',
                }}
              >
                Triggers Step-Up
              </span>
            </button>
          )}

          {isDarth && (
            <>
              <button
                disabled={isLoading}
                onClick={() =>
                  onExecuteRequest({
                    method: 'DELETE',
                    endpoint: '/api/v1/documents/doc_eng_specs',
                    label: 'Darth Ransomware Deletion Attempt',
                  })
                }
                style={{
                  background: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  color: '#fff',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Skull size={18} color="var(--color-deny)" />
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600 }}>Ransomware Mutation (Delete Specs)</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                      DELETE /api/v1/documents/doc_eng_specs
                    </div>
                  </div>
                </div>
                <span
                  style={{
                    fontSize: '11px',
                    color: 'var(--color-deny)',
                    background: 'var(--color-deny-bg)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                  }}
                >
                  Hard Block
                </span>
              </button>

              <button
                disabled={isLoading}
                onClick={() =>
                  onExecuteRequest({
                    method: 'POST',
                    endpoint: '/api/v1/admin/purge-cache',
                    label: 'Darth Attempting Admin Takeover',
                  })
                }
                style={{
                  background: 'rgba(239, 68, 68, 0.08)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  textAlign: 'left',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  color: '#fff',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Terminal size={18} color="var(--color-deny)" />
                  <div>
                    <div style={{ fontSize: '13px', fontWeight: 600 }}>Unauthorized Admin Takeover (Purge Cache)</div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                      POST /api/v1/admin/purge-cache
                    </div>
                  </div>
                </div>
                <span
                  style={{
                    fontSize: '11px',
                    color: 'var(--color-deny)',
                    background: 'var(--color-deny-bg)',
                    padding: '2px 8px',
                    borderRadius: '4px',
                  }}
                >
                  Denied
                </span>
              </button>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
