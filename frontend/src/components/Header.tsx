import React from 'react';
import { Shield, RefreshCw } from 'lucide-react';

interface HeaderProps {
  autoRefresh: boolean;
  onToggleAutoRefresh: () => void;
  onManualRefresh: () => void;
  lastUpdated: Date;
}

export const Header: React.FC<HeaderProps> = ({
  autoRefresh,
  onToggleAutoRefresh,
  onManualRefresh,
  lastUpdated,
}) => {
  return (
    <header className="glass-panel nav-header" style={{ marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div
          style={{
            background: 'var(--primary)',
            padding: '8px',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Shield size={22} color="#fff" />
        </div>
        <div>
          <h1 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0 }}>
            API Gateway Admin Console
          </h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '2px' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Connected to Local MongoDB (localhost:27017)
            </span>
            <span style={{ color: 'var(--text-dim)' }}>•</span>
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '5px',
                fontSize: '0.75rem',
                color: 'var(--color-allow)',
                fontWeight: 600,
              }}
            >
              <span
                style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--color-allow)',
                }}
                className="pulse"
              />
              ONLINE
            </span>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: 'rgba(15, 23, 42, 0.6)',
            padding: '6px 12px',
            borderRadius: '6px',
            border: '1px solid var(--card-border)',
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
          }}
        >
          <span>Control Plane: <strong className="mono" style={{ color: 'var(--text-main)' }}>:3002</strong></span>
          <span style={{ color: 'var(--text-dim)' }}>|</span>
          <span>Data Plane: <strong className="mono" style={{ color: 'var(--text-main)' }}>:3003</strong></span>
          <span style={{ color: 'var(--text-dim)' }}>|</span>
          <span>SpiceDB: <strong className="mono" style={{ color: 'var(--text-main)' }}>:50051</strong></span>
        </div>

        <button
          onClick={onToggleAutoRefresh}
          className="tab-btn"
          style={{
            border: '1px solid var(--card-border)',
            padding: '6px 12px',
            fontSize: '0.75rem',
            background: autoRefresh ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
            color: autoRefresh ? 'var(--primary)' : 'var(--text-muted)',
          }}
        >
          <span
            style={{
              width: '7px',
              height: '7px',
              borderRadius: '50%',
              backgroundColor: autoRefresh ? 'var(--color-allow)' : 'var(--text-dim)',
            }}
          />
          Auto-Sync {autoRefresh ? '4s' : 'Off'}
        </button>

        <button
          onClick={onManualRefresh}
          className="tab-btn"
          title={`Last refreshed at ${lastUpdated.toLocaleTimeString()}`}
          style={{ border: '1px solid var(--card-border)', padding: '6px 12px', fontSize: '0.75rem' }}
        >
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>
    </header>
  );
};
