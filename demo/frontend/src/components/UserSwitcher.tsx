import { Users } from 'lucide-react';
import { SubjectId, SimulatorUser } from '../types';

interface UserSwitcherProps {
  users: SimulatorUser[];
  currentUser: SubjectId;
  onSelectUser: (user: SubjectId) => void;
}

export function UserSwitcher({ users, currentUser, onSelectUser }: UserSwitcherProps) {
  return (
    <section className="glass-panel" style={{ padding: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Users size={18} color="var(--color-cyan)" />
          <h2 style={{ fontSize: '15px', fontWeight: 600 }}>Active Subject Identity</h2>
        </div>
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Token: Bearer {currentUser}</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
        {users.map((user) => {
          const active = currentUser === user.id;
          return (
            <div
              key={user.id}
              onClick={() => onSelectUser(user.id)}
              style={{
                background: active ? 'rgba(6, 182, 212, 0.08)' : 'var(--bg-secondary)',
                border: `1px solid ${active ? 'var(--color-cyan)' : 'var(--border-subtle)'}`,
                borderRadius: '12px',
                padding: '16px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '14px',
                transition: 'all 0.2s ease',
                boxShadow: active ? '0 0 20px rgba(6, 182, 212, 0.2)' : 'none'
              }}
            >
              <div style={{
                width: '42px',
                height: '42px',
                borderRadius: '10px',
                background: user.avatarColor,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '14px',
                color: '#fff',
                flexShrink: 0
              }}>
                {user.initials}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontWeight: 600, fontSize: '14px' }}>{user.name}</span>
                  {active && (
                    <span style={{
                      fontSize: '10px',
                      textTransform: 'uppercase',
                      fontWeight: 700,
                      padding: '2px 6px',
                      background: 'rgba(6, 182, 212, 0.2)',
                      color: 'var(--color-cyan)',
                      borderRadius: '4px'
                    }}>
                      Active
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {user.role} &bull; {user.department}
                </div>
                <div style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {user.id}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
