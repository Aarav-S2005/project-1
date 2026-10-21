import React, { useState, useEffect } from 'react';
import type { AuditRecord, UserTrustProfile, RuntimeParameters } from '../types';
import {
  fetchUsersTrustScores,
  fetchUserRequestHistory,
  resetUserTrust,
  fetchRuntimeParameters,
  updateRuntimeParameters,
  setUserTrustScore,
  resetAllTrustAndAudit,
} from '../api';
import { ShapExplainer } from './ShapExplainer';
import {
  Users,
  RotateCcw,
  ChevronRight,
  ChevronDown,
  Search,
  Sliders,
  Save,
  CheckCircle,
  SlidersHorizontal,
  Trash2,
} from 'lucide-react';


export const UsersTrustManager: React.FC = () => {
  const [users, setUsers] = useState<UserTrustProfile[]>([]);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [history, setHistory] = useState<AuditRecord[]>([]);
  const [expandedRequestId, setExpandedRequestId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [resettingUser, setResettingUser] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Runtime parameters configuration in Control Plane
  const [showParamsPanel, setShowParamsPanel] = useState(false);
  const [params, setParams] = useState<RuntimeParameters>({
    half_life_seconds: 300,
    anomaly_weight: 0.4,
    narrow_band_threshold: 0.85,
    step_up_band_threshold: 0.60,
    narrow_ttl_seconds: 60,
  });
  const [paramsSaving, setParamsSaving] = useState(false);
  const [paramsSaved, setParamsSaved] = useState(false);

  // Per-user manual trust score adjustment
  const [userScoreInput, setUserScoreInput] = useState<number>(1.0);
  const [updatingUserScore, setUpdatingUserScore] = useState(false);
  const [globalResetting, setGlobalResetting] = useState(false);


  const loadUsers = async () => {
    setLoading(true);
    try {
      const data = await fetchUsersTrustScores();
      setUsers(data);
      if (!selectedUser && data.length > 0) {
        setSelectedUser(data[0].subject_id);
      }
    } catch (err) {
      console.warn('Failed to load user trust scores:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadParams = async () => {
    try {
      const data = await fetchRuntimeParameters();
      setParams(data);
    } catch (err) {
      console.warn('Failed to load runtime parameters:', err);
    }
  };

  const loadHistory = async (subjectId: string) => {
    setHistoryLoading(true);
    try {
      const records = await fetchUserRequestHistory(subjectId);
      setHistory(records);
      if (records.length > 0) {
        setExpandedRequestId(records[0].request_id);
      }
    } catch (err) {
      console.warn('Failed to load user history:', err);
      setHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    loadUsers();
    loadParams();
  }, []);

  useEffect(() => {
    if (selectedUser) {
      loadHistory(selectedUser);
      const profile = users.find((u) => u.subject_id === selectedUser);
      if (profile) {
        setUserScoreInput(profile.current_trust_score);
      }
    }
  }, [selectedUser, users]);

  const handleResetTrust = async (subjectId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`Reset trust score for '${subjectId}' back to baseline (1.0)?`)) return;
    setResettingUser(subjectId);
    try {
      await resetUserTrust(subjectId);
      await loadUsers();
      if (selectedUser === subjectId) {
        await loadHistory(subjectId);
        setUserScoreInput(1.0);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to reset trust score');
    } finally {
      setResettingUser(null);
    }
  };

  const handleApplyUserTrustScore = async () => {
    if (!selectedUser) return;
    setUpdatingUserScore(true);
    try {
      await setUserTrustScore(selectedUser, userScoreInput);
      await loadUsers();
      if (selectedUser) {
        await loadHistory(selectedUser);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to update user trust score');
    } finally {
      setUpdatingUserScore(false);
    }
  };

  const handleSaveParams = async () => {
    setParamsSaving(true);
    try {
      await updateRuntimeParameters(params);
      setParamsSaved(true);
      setTimeout(() => setParamsSaved(false), 2500);
    } catch (err: any) {
      alert(err.message || 'Failed to save runtime trust parameters');
    } finally {
      setParamsSaving(false);
    }
  };

  const handleGlobalReset = async (targetScore: number) => {
    const isZero = targetScore === 0.0;
    const confirmMsg = isZero
      ? 'Are you sure? This will WIPE all audit logs from MongoDB and set ALL users trust score to 0.0 (Zero-Trust Untrusted).'
      : 'Are you sure? This will WIPE all audit logs from MongoDB and restore ALL users trust score to 1.0 (Full Trust Baseline).';

    if (!window.confirm(confirmMsg)) return;

    setGlobalResetting(true);
    try {
      await resetAllTrustAndAudit(targetScore);
      await loadUsers();
      if (selectedUser) {
        await loadHistory(selectedUser);
      }
      setUserScoreInput(targetScore);
    } catch (err: any) {
      alert(err.message || 'Failed to perform global reset');
    } finally {
      setGlobalResetting(false);
    }
  };


  const getScoreColor = (score: number) => {
    if (score >= 0.85) return 'var(--color-allow)';
    if (score >= 0.60) return 'var(--color-narrow)';
    if (score >= 0.40) return 'var(--color-stepup)';
    return 'var(--color-deny)';
  };

  const getScoreBandLabel = (score: number) => {
    if (score >= 0.85) return 'Nominal (High Trust)';
    if (score >= 0.60) return 'Narrowed (Graph Restricting)';
    if (score >= 0.40) return 'Challenged (Step-Up MFA)';
    return 'Critical (Access Denied)';
  };

  const filteredUsers = users.filter((u) => {
    if (!searchQuery) return true;
    return u.subject_id.toLowerCase().includes(searchQuery.toLowerCase());
  });

  const activeUserProfile = users.find((u) => u.subject_id === selectedUser);

  return (
    <div>
      {/* Title & Toolbar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Users size={18} color="var(--primary)" />
            User Continuous Trust Scores & Anomaly Explanations
          </h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Real-time stateful trust decay, decision history, and SHAP feature-level attribution
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <button
            onClick={() => setShowParamsPanel(!showParamsPanel)}
            className="tab-btn"
            style={{
              padding: '6px 12px',
              fontSize: '0.8rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: showParamsPanel ? 'rgba(99, 102, 241, 0.2)' : 'rgba(15, 23, 42, 0.7)',
              border: showParamsPanel ? '1px solid var(--primary)' : '1px solid var(--card-border)',
              color: showParamsPanel ? '#fff' : 'var(--text-muted)',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            <Sliders size={14} color={showParamsPanel ? 'var(--primary)' : 'currentColor'} />
            Configure Trust Parameters
          </button>

          <button
            onClick={() => handleGlobalReset(0.0)}
            disabled={globalResetting}
            title="Clear all MongoDB audit records and set all users trust score to 0.0 (Untrusted / Denied)"
            style={{
              padding: '6px 12px',
              fontSize: '0.8rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              color: '#f87171',
              borderRadius: '6px',
              cursor: globalResetting ? 'not-allowed' : 'pointer',
              fontWeight: 500,
            }}
          >
            <Trash2 size={14} />
            {globalResetting ? 'Processing...' : 'Clear Logs & Set All to 0.0'}
          </button>

          <button
            onClick={() => handleGlobalReset(1.0)}
            disabled={globalResetting}
            title="Clear all MongoDB audit records and restore all users trust score to 1.0 (Full Trust Baseline)"
            style={{
              padding: '6px 12px',
              fontSize: '0.8rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid rgba(16, 185, 129, 0.4)',
              color: '#34d399',
              borderRadius: '6px',
              cursor: globalResetting ? 'not-allowed' : 'pointer',
              fontWeight: 500,
            }}
          >
            <RotateCcw size={14} />
            Restore All to 1.0
          </button>

          <div style={{ position: 'relative', minWidth: '200px' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '9px', color: 'var(--text-dim)' }} />
            <input
              type="text"
              placeholder="Search users..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                padding: '6px 10px 6px 30px',
                borderRadius: '6px',
                background: '#0b0f17',
                border: '1px solid var(--card-border)',
                color: '#fff',
                fontSize: '0.8rem',
              }}
            />
          </div>
        </div>
      </div>

      {/* Collapsible Control Plane Parameter Sliders Panel */}
      {showParamsPanel && (
        <div
          className="glass-panel"
          style={{
            padding: '20px',
            marginBottom: '20px',
            background: 'rgba(15, 23, 42, 0.95)',
            border: '1px solid var(--primary)',
            borderRadius: '10px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <SlidersHorizontal size={18} color="var(--primary)" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>
                Control Plane: Trust Scoring & Decision Threshold Parameters (Redis)
              </h3>
            </div>
            <button
              onClick={handleSaveParams}
              disabled={paramsSaving}
              className="btn-primary"
              style={{
                fontSize: '0.78rem',
                padding: '6px 14px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              {paramsSaved ? <CheckCircle size={14} color="#22c55e" /> : <Save size={14} />}
              {paramsSaved ? 'Saved to Redis!' : paramsSaving ? 'Saving...' : 'Save Parameters'}
            </button>
          </div>

          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '16px', lineHeight: 1.5 }}>
            Adjust continuous decay rates, anomaly penalties, and decision band thresholds. These live parameters are saved to Redis (<code className="mono">trust:runtime_parameters</code>) and hot-reloaded by the Data Plane trust engine.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
            {/* Half-Life */}
            <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '12px', borderRadius: '8px', border: '1px solid var(--card-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '6px' }}>
                <span style={{ fontWeight: 600 }}>Trust Half-Life (Decay):</span>
                <span className="mono" style={{ color: 'var(--primary)', fontWeight: 700 }}>{params.half_life_seconds}s</span>
              </div>
              <input
                type="range"
                min="30"
                max="1800"
                step="30"
                value={params.half_life_seconds}
                onChange={(e) => setParams({ ...params, half_life_seconds: parseFloat(e.target.value) })}
                style={{ width: '100%', cursor: 'pointer' }}
              />
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                Time for trust score to naturally decay halfway to baseline (30s - 30min).
              </div>
            </div>

            {/* Anomaly Weight */}
            <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '12px', borderRadius: '8px', border: '1px solid var(--card-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '6px' }}>
                <span style={{ fontWeight: 600 }}>Anomaly Penalty Weight:</span>
                <span className="mono" style={{ color: 'var(--color-deny)', fontWeight: 700 }}>{params.anomaly_weight.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.05"
                max="1.0"
                step="0.05"
                value={params.anomaly_weight}
                onChange={(e) => setParams({ ...params, anomaly_weight: parseFloat(e.target.value) })}
                style={{ width: '100%', cursor: 'pointer' }}
              />
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                Penalty deducted when Isolation Forest flags an anomaly.
              </div>
            </div>

            {/* Narrow Band Threshold */}
            <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '12px', borderRadius: '8px', border: '1px solid var(--card-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '6px' }}>
                <span style={{ fontWeight: 600 }}>Narrow Band Threshold:</span>
                <span className="mono" style={{ color: 'var(--color-narrow)', fontWeight: 700 }}>{params.narrow_band_threshold.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.50"
                max="0.95"
                step="0.05"
                value={params.narrow_band_threshold}
                onChange={(e) => setParams({ ...params, narrow_band_threshold: parseFloat(e.target.value) })}
                style={{ width: '100%', cursor: 'pointer' }}
              />
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                Scores below this trigger temporary ReBAC narrow restrictions in SpiceDB.
              </div>
            </div>

            {/* Step-Up MFA Threshold */}
            <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '12px', borderRadius: '8px', border: '1px solid var(--card-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '6px' }}>
                <span style={{ fontWeight: 600 }}>Step-Up MFA Band:</span>
                <span className="mono" style={{ color: 'var(--color-stepup)', fontWeight: 700 }}>{params.step_up_band_threshold.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="0.20"
                max="0.80"
                step="0.05"
                value={params.step_up_band_threshold}
                onChange={(e) => setParams({ ...params, step_up_band_threshold: parseFloat(e.target.value) })}
                style={{ width: '100%', cursor: 'pointer' }}
              />
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                Scores below this challenge the client with an MFA Step-Up verification.
              </div>
            </div>

            {/* Narrow TTL */}
            <div style={{ background: 'rgba(0, 0, 0, 0.25)', padding: '12px', borderRadius: '8px', border: '1px solid var(--card-border)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: '6px' }}>
                <span style={{ fontWeight: 600 }}>Narrow Restriction TTL:</span>
                <span className="mono" style={{ color: '#a5b4fc', fontWeight: 700 }}>{params.narrow_ttl_seconds}s</span>
              </div>
              <input
                type="range"
                min="10"
                max="600"
                step="10"
                value={params.narrow_ttl_seconds}
                onChange={(e) => setParams({ ...params, narrow_ttl_seconds: parseInt(e.target.value) })}
                style={{ width: '100%', cursor: 'pointer' }}
              />
              <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '4px' }}>
                Duration before temporary restricting relations expire from SpiceDB.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Split View: Left = Users List, Right = Selected User Detail & Request Explanations */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 380px) 1fr', gap: '18px', alignItems: 'start' }}>
        {/* Left Column: Users Cards List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {filteredUsers.length === 0 ? (
            <div className="glass-panel" style={{ padding: '24px', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
              {loading ? 'Loading user profiles...' : 'No user requests recorded yet. Send requests through Gateway (:3003) to begin tracking continuous trust scores.'}
            </div>
          ) : (
            filteredUsers.map((user) => {
              const isSelected = selectedUser === user.subject_id;
              const scoreColor = getScoreColor(user.current_trust_score);

              return (
                <div
                  key={user.subject_id}
                  onClick={() => setSelectedUser(user.subject_id)}
                  className="glass-panel"
                  style={{
                    padding: '14px 16px',
                    cursor: 'pointer',
                    background: isSelected ? 'rgba(99, 102, 241, 0.15)' : 'rgba(15, 23, 42, 0.7)',
                    border: isSelected ? '1px solid var(--primary)' : '1px solid var(--card-border)',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div
                        style={{
                          width: '10px',
                          height: '10px',
                          borderRadius: '50%',
                          backgroundColor: scoreColor,
                        }}
                      />
                      <span className="mono" style={{ fontSize: '0.9rem', fontWeight: 700, color: '#fff' }}>
                        {user.subject_id}
                      </span>
                    </div>

                    <span
                      className="mono"
                      style={{
                        fontSize: '1.05rem',
                        fontWeight: 700,
                        color: scoreColor,
                      }}
                    >
                      {user.current_trust_score.toFixed(2)}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
                    Band: <strong style={{ color: scoreColor }}>{getScoreBandLabel(user.current_trust_score)}</strong>
                  </div>

                  {/* Trust Score Progress Bar */}
                  <div
                    style={{
                      width: '100%',
                      height: '6px',
                      background: 'rgba(255, 255, 255, 0.1)',
                      borderRadius: '3px',
                      overflow: 'hidden',
                      marginBottom: '10px',
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.min(100, Math.max(5, user.current_trust_score * 100))}%`,
                        height: '100%',
                        backgroundColor: scoreColor,
                        transition: 'width 0.3s ease',
                      }}
                    />
                  </div>

                  {/* Meta pills & Reset button */}
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.72rem' }}>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <span style={{ color: 'var(--text-dim)' }}>{user.total_requests} reqs</span>
                      {user.anomalous_requests > 0 && (
                        <span style={{ color: 'var(--color-deny)', fontWeight: 600 }}>
                          • {user.anomalous_requests} anomalies
                        </span>
                      )}
                      {user.is_restricted && (
                        <span style={{ background: 'rgba(234, 179, 8, 0.2)', color: '#facc15', padding: '1px 5px', borderRadius: '4px', fontWeight: 600 }}>
                          Restricted in SpiceDB
                        </span>
                      )}
                    </div>

                    <button
                      onClick={(e) => handleResetTrust(user.subject_id, e)}
                      disabled={resettingUser === user.subject_id}
                      className="tab-btn"
                      title="Reset trust score to 1.0 baseline in Redis"
                      style={{
                        padding: '3px 8px',
                        fontSize: '0.7rem',
                        border: '1px solid var(--card-border)',
                        color: '#a5b4fc',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px',
                      }}
                    >
                      <RotateCcw size={11} />
                      Reset
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Right Column: Selected User Detail & Request Explanations */}
        <div>
          {activeUserProfile ? (
            <div>
              {/* Active User Overview & Manual Trust Override Card */}
              <div className="glass-panel" style={{ padding: '16px 20px', marginBottom: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginBottom: '14px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <h3 style={{ fontSize: '1.05rem', fontWeight: 700, margin: 0 }} className="mono">
                        {activeUserProfile.subject_id}
                      </h3>
                      <span
                        style={{
                          fontSize: '0.72rem',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontWeight: 700,
                          background: getScoreColor(activeUserProfile.current_trust_score) + '25',
                          color: getScoreColor(activeUserProfile.current_trust_score),
                        }}
                      >
                        Score: {activeUserProfile.current_trust_score.toFixed(3)}
                      </span>
                      {activeUserProfile.is_restricted && (
                        <span style={{ fontSize: '0.72rem', padding: '2px 8px', borderRadius: '4px', background: 'rgba(234, 179, 8, 0.2)', color: '#facc15', fontWeight: 700 }}>
                          Restricted in SpiceDB ReBAC
                        </span>
                      )}
                    </div>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block', marginTop: '4px' }}>
                      {getScoreBandLabel(activeUserProfile.current_trust_score)} • Last Seen: {new Date(activeUserProfile.last_seen).toLocaleTimeString()}
                    </span>
                  </div>

                  <button
                    onClick={(e) => handleResetTrust(activeUserProfile.subject_id, e)}
                    className="btn-primary"
                    style={{ fontSize: '0.78rem', padding: '6px 12px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                  >
                    <RotateCcw size={13} />
                    Restore Trust to 1.0
                  </button>
                </div>

                {/* Per-User Trust Slider & Manual Override */}
                <div
                  style={{
                    background: 'rgba(0, 0, 0, 0.3)',
                    border: '1px solid var(--card-border)',
                    borderRadius: '8px',
                    padding: '12px 14px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-main)' }}>
                      Operator Trust Override for {activeUserProfile.subject_id}:
                    </span>
                    <span className="mono" style={{ fontSize: '0.85rem', fontWeight: 700, color: getScoreColor(userScoreInput) }}>
                      {userScoreInput.toFixed(2)}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <input
                      type="range"
                      min="0.0"
                      max="1.0"
                      step="0.05"
                      value={userScoreInput}
                      onChange={(e) => setUserScoreInput(parseFloat(e.target.value))}
                      style={{ flex: 1, cursor: 'pointer' }}
                    />
                    <button
                      onClick={handleApplyUserTrustScore}
                      disabled={updatingUserScore}
                      className="tab-btn"
                      style={{
                        padding: '4px 10px',
                        fontSize: '0.72rem',
                        border: '1px solid var(--primary)',
                        color: 'var(--primary)',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {updatingUserScore ? 'Applying...' : 'Apply Trust Score'}
                    </button>
                  </div>
                </div>
              </div>

              {/* Request History with SHAP Explainers */}
              <div className="glass-panel" style={{ padding: '16px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <span style={{ fontSize: '0.88rem', fontWeight: 600 }}>
                    Requests History & Feature-Level Attribution ({history.length} records)
                  </span>
                  <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                    Click any request to expand SHAP attribution
                  </span>
                </div>

                {historyLoading ? (
                  <div style={{ textAlign: 'center', padding: '28px', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
                    Loading request history and SHAP attributions...
                  </div>
                ) : history.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '28px', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
                    No audit records logged for this user yet. Send requests through the Data Plane (:3003) to generate audit logs.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {history.map((record) => {
                      const isExpanded = expandedRequestId === record.request_id;
                      const hasAttribution = record.shap_attributions && Object.keys(record.shap_attributions).length > 0;
                      const scoreDelta = (record.trust_score_after ?? 0) - (record.trust_score_before ?? 0);

                      return (
                        <div
                          key={record.request_id}
                          style={{
                            background: isExpanded ? 'rgba(15, 23, 42, 0.9)' : 'rgba(0, 0, 0, 0.25)',
                            border: isExpanded ? '1px solid var(--primary)' : '1px solid var(--card-border)',
                            borderRadius: '8px',
                            overflow: 'hidden',
                            transition: 'all 0.15s ease',
                          }}
                        >
                          {/* Request Summary Row (Clickable) */}
                          <div
                            onClick={() => setExpandedRequestId(isExpanded ? null : record.request_id)}
                            style={{
                              padding: '12px 14px',
                              cursor: 'pointer',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              gap: '10px',
                              flexWrap: 'wrap',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              {isExpanded ? <ChevronDown size={15} color="var(--primary)" /> : <ChevronRight size={15} color="var(--text-dim)" />}
                              <div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                  <span
                                    style={{
                                      fontSize: '0.72rem',
                                      fontWeight: 700,
                                      padding: '1px 6px',
                                      borderRadius: '4px',
                                      textTransform: 'uppercase',
                                      background:
                                        record.decision === 'allow'
                                          ? 'rgba(34, 197, 94, 0.2)'
                                          : record.decision === 'narrow'
                                          ? 'rgba(234, 179, 8, 0.2)'
                                          : record.decision === 'step_up'
                                          ? 'rgba(249, 115, 22, 0.2)'
                                          : 'rgba(239, 68, 68, 0.2)',
                                      color:
                                        record.decision === 'allow'
                                          ? 'var(--color-allow)'
                                          : record.decision === 'narrow'
                                          ? 'var(--color-narrow)'
                                          : record.decision === 'step_up'
                                          ? 'var(--color-stepup)'
                                          : 'var(--color-deny)',
                                    }}
                                  >
                                    {record.decision}
                                  </span>
                                  <span className="mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff' }}>
                                    {record.resource}
                                  </span>
                                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                    ({record.permission})
                                  </span>
                                </div>
                                <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)', display: 'block', marginTop: '2px' }} className="mono">
                                  {record.request_id} • {new Date(record.timestamp).toLocaleTimeString()} • {record.latency_ms.toFixed(2)}ms
                                </span>
                              </div>
                            </div>

                            {/* Trust Score Transition Gauge */}
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                              <div style={{ textAlign: 'right' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                  <span className="mono" style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                                    {(record.trust_score_before ?? 1.0).toFixed(2)}
                                  </span>
                                  <span style={{ color: 'var(--text-dim)', fontSize: '0.75rem' }}>➔</span>
                                  <span
                                    className="mono"
                                    style={{
                                      fontSize: '0.85rem',
                                      fontWeight: 700,
                                      color: getScoreColor(record.trust_score_after ?? 1.0),
                                    }}
                                  >
                                    {(record.trust_score_after ?? 1.0).toFixed(2)}
                                  </span>
                                </div>
                                <span
                                  style={{
                                    fontSize: '0.68rem',
                                    color: scoreDelta < 0 ? 'var(--color-deny)' : (scoreDelta > 0 ? 'var(--color-allow)' : 'var(--text-dim)'),
                                    fontWeight: 600,
                                  }}
                                >
                                  {scoreDelta > 0 ? `+${scoreDelta.toFixed(3)}` : (scoreDelta < 0 ? scoreDelta.toFixed(3) : 'No change')}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Expanded Section: SHAP Feature Attribution Breakdown */}
                          {isExpanded && (
                            <div style={{ padding: '14px 16px', borderTop: '1px solid var(--card-border)', background: 'rgba(0, 0, 0, 0.4)' }}>
                              <div style={{ marginBottom: '12px' }}>
                                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Decision Rationale:</span>
                                <span className="mono" style={{ fontSize: '0.78rem', color: '#a5b4fc', marginLeft: '6px' }}>
                                  {record.decision_reason}
                                </span>
                              </div>

                              {/* SHAP Explainer Chart */}
                              {hasAttribution ? (
                                <div>
                                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-main)', display: 'block', marginBottom: '8px' }}>
                                    SHAP Feature Attribution (Why trust score changed):
                                  </span>
                                  <ShapExplainer
                                    attributions={record.shap_attributions}
                                    scoreBefore={record.trust_score_before ?? 1.0}
                                    scoreAfter={record.trust_score_after ?? 1.0}
                                  />
                                </div>
                              ) : (
                                <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>
                                  No SHAP features generated for this decision.
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="glass-panel" style={{ padding: '40px', textAlign: 'center', color: 'var(--text-dim)' }}>
              Select a user on the left to view detailed trust score progression, SHAP explanations, and request history.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
