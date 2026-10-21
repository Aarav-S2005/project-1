import React from 'react';

interface ShapExplainerProps {
  attributions: Record<string, number>;
  scoreBefore: number;
  scoreAfter: number;
}

export const ShapExplainer: React.FC<ShapExplainerProps> = ({
  attributions,
  scoreBefore,
  scoreAfter,
}) => {
  const entries = Object.entries(attributions || {}).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const maxVal = Math.max(...entries.map(([, v]) => Math.abs(v)), 0.05);

  const formatFeatureName = (key: string) => {
    return key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase());
  };

  return (
    <div
      style={{
        background: 'rgba(15, 23, 42, 0.7)',
        padding: '16px',
        borderRadius: '10px',
        border: '1px solid var(--card-border)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
          SHAP Feature Attribution (TreeExplainer)
        </span>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
          Score Delta:{' '}
          <span
            style={{
              fontWeight: 700,
              color: scoreAfter >= scoreBefore ? 'var(--color-allow)' : 'var(--color-deny)',
            }}
          >
            {(scoreAfter - scoreBefore) >= 0 ? '+' : ''}
            {(scoreAfter - scoreBefore).toFixed(4)}
          </span>
        </div>
      </div>

      {entries.length === 0 ? (
        <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', textAlign: 'center', padding: '12px 0' }}>
          No prominent feature anomalies recorded for this decision.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {entries.slice(0, 5).map(([feature, val]) => {
            const isNegativeImpact = val < 0; // Negative SHAP in Isolation Forest means more anomalous
            const pct = Math.min(100, Math.round((Math.abs(val) / maxVal) * 100));

            return (
              <div key={feature} style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '0.75rem' }}>
                <span
                  style={{
                    width: '160px',
                    color: 'var(--text-muted)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                  title={feature}
                >
                  {formatFeatureName(feature)}
                </span>
                <div
                  style={{
                    flex: 1,
                    height: '8px',
                    background: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: '4px',
                    overflow: 'hidden',
                    position: 'relative',
                  }}
                >
                  <div
                    style={{
                      width: `${pct}%`,
                      height: '100%',
                      background: isNegativeImpact ? 'var(--color-deny)' : 'var(--color-allow)',
                      borderRadius: '4px',
                      transition: 'width 0.4s ease',
                    }}
                  />
                </div>
                <span
                  className="mono"
                  style={{
                    width: '60px',
                    textAlign: 'right',
                    color: isNegativeImpact ? 'var(--color-deny)' : 'var(--color-allow)',
                    fontWeight: 600,
                  }}
                >
                  {val >= 0 ? '+' : ''}
                  {val.toFixed(4)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
