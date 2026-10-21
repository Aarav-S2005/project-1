import { useState } from 'react';
import { KeyRound, ShieldAlert, CheckCircle2, X } from 'lucide-react';
import { SubjectId } from '../types';

interface StepUpModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentUser: SubjectId;
  onSuccess: () => void;
}

export function StepUpModal({ isOpen, onClose, currentUser, onSuccess }: StepUpModalProps) {
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (code.trim() !== '123456') {
      setError('Invalid MFA Passcode. Please enter standard test code: 123456');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`http://localhost:3002/api/v1/users/${currentUser}/reset-trust`, {
        method: 'POST',
      });

      if (res.ok) {
        setSuccess(true);
        setTimeout(() => {
          setSuccess(false);
          setCode('');
          onSuccess();
          onClose();
        }, 1200);
      } else {
        const text = await res.text();
        setError(`Failed to reset trust on Control Plane: ${text}`);
      }
    } catch (err: any) {
      setError(`Network error contacting Control Plane: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
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
      zIndex: 100,
      padding: '16px'
    }}>
      <div style={{
        background: '#0d131f',
        border: '1px solid var(--color-step-up)',
        borderRadius: '16px',
        padding: '24px',
        width: '100%',
        maxWidth: '420px',
        boxShadow: '0 0 32px rgba(245, 158, 11, 0.3)',
        position: 'relative'
      }}>
        <button
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer'
          }}
        >
          <X size={18} />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
          <div style={{
            background: 'var(--color-step-up-bg)',
            padding: '10px',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <ShieldAlert size={24} color="var(--color-step-up)" />
          </div>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#fff' }}>Step-Up Authentication Required</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Trust score has dropped below challenge threshold</p>
          </div>
        </div>

        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px', lineHeight: 1.5 }}>
          The Gateway detected anomalous behavior for active subject <strong style={{ color: '#fff' }}>{currentUser}</strong>.
          Complete multi-factor authentication challenge to restore session trust.
        </p>

        {success ? (
          <div style={{
            background: 'var(--color-allow-bg)',
            border: '1px solid var(--color-allow)',
            borderRadius: '8px',
            padding: '16px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            color: 'var(--color-allow)',
            fontSize: '13px',
            fontWeight: 600
          }}>
            <CheckCircle2 size={20} />
            MFA Challenge Verified! Trust score restored to 1.0 (100%).
          </div>
        ) : (
          <form onSubmit={handleVerify}>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                Enter MFA Passcode (Simulator code: <strong>123456</strong>)
              </label>
              <div style={{ position: 'relative' }}>
                <input
                  type="text"
                  maxLength={6}
                  placeholder="123456"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  autoFocus
                  style={{
                    width: '100%',
                    background: 'var(--bg-secondary)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: '8px',
                    padding: '10px 12px 10px 38px',
                    fontSize: '18px',
                    letterSpacing: '4px',
                    fontFamily: 'var(--font-mono)',
                    color: '#fff',
                    outline: 'none',
                  }}
                />
                <KeyRound size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '14px' }} />
              </div>
            </div>

            {error && (
              <div style={{ color: 'var(--color-deny)', fontSize: '12px', marginBottom: '12px' }}>
                {error}
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
              <button
                type="button"
                onClick={onClose}
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: '6px',
                  padding: '8px 16px',
                  fontSize: '13px',
                  color: 'var(--text-secondary)',
                }}
              >
                Dismiss
              </button>
              <button
                type="submit"
                disabled={loading || code.length < 6}
                style={{
                  background: 'var(--color-step-up)',
                  borderRadius: '6px',
                  padding: '8px 20px',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: '#000',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                {loading ? 'Verifying...' : 'Verify MFA'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
