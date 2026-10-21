import React, { useState, useEffect } from 'react';
import type { RebacRelationship, UserAccessInfo } from '../types';
import {
  fetchRebacRelationships,
  createRebacRelationship,
  deleteRebacRelationship,
  fetchUserAccess,
} from '../api';
import {
  Share2,
  Plus,
  Trash2,
  UserCheck,
  Shield,
  FileText,
  Search,
  CheckCircle,
  XCircle,
} from 'lucide-react';

interface RebacGraphManagerProps {
  onRefresh?: () => void;
}

export const RebacGraphManager: React.FC<RebacGraphManagerProps> = () => {
  const [relationships, setRelationships] = useState<RebacRelationship[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterQuery, setFilterQuery] = useState('');

  // Form State
  const [showAddForm, setShowAddForm] = useState(false);
  const [resourceType, setResourceType] = useState('document');
  const [resourceId, setResourceId] = useState('doc_1');
  const [relation, setRelation] = useState('viewer');
  const [subjectType, setSubjectType] = useState('user');
  const [subjectId, setSubjectId] = useState('alice');

  // User Access Inspector State
  const [inspectUser, setInspectUser] = useState('user:alice');
  const [userAccess, setUserAccess] = useState<UserAccessInfo[]>([]);
  const [inspectLoading, setInspectLoading] = useState(false);

  const loadRelationships = async () => {
    setLoading(true);
    try {
      const data = await fetchRebacRelationships();
      setRelationships(data);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to load SpiceDB relationships');
    } finally {
      setLoading(false);
    }
  };

  const loadUserAccess = async (user: string) => {
    setInspectLoading(true);
    try {
      const data = await fetchUserAccess(user);
      setUserAccess(data);
    } catch {
      setUserAccess([]);
    } finally {
      setInspectLoading(false);
    }
  };

  useEffect(() => {
    loadRelationships();
  }, []);

  useEffect(() => {
    if (inspectUser) {
      loadUserAccess(inspectUser);
    }
  }, [inspectUser]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resourceId || !subjectId) return;

    setLoading(true);
    setError(null);
    try {
      await createRebacRelationship({
        resource_type: resourceType.trim(),
        resource_id: resourceId.trim(),
        relation: relation.trim(),
        subject_type: subjectType.trim(),
        subject_id: subjectId.trim(),
      });
      setShowAddForm(false);
      await loadRelationships();
      if (inspectUser.includes(subjectId)) {
        await loadUserAccess(inspectUser);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create relationship in SpiceDB');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (rel: RebacRelationship) => {
    if (!window.confirm(`Delete relationship '${rel.tuple}' from SpiceDB?`)) return;
    try {
      await deleteRebacRelationship({
        resource_type: rel.resource_type,
        resource_id: rel.resource_id,
        relation: rel.relation,
        subject_type: rel.subject_type,
        subject_id: rel.subject_id,
      });
      await loadRelationships();
      if (inspectUser.includes(rel.subject_id)) {
        await loadUserAccess(inspectUser);
      }
    } catch (err: any) {
      alert(err.message || 'Failed to delete relationship');
    }
  };

  const filteredRels = relationships.filter((r) => {
    if (!filterQuery) return true;
    const q = filterQuery.toLowerCase();
    return (
      r.tuple.toLowerCase().includes(q) ||
      r.subject_id.toLowerCase().includes(q) ||
      r.resource_id.toLowerCase().includes(q) ||
      r.relation.toLowerCase().includes(q)
    );
  });

  return (
    <div>
      {/* Top Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ fontSize: '1.15rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Share2 size={18} color="var(--primary)" />
            SpiceDB ReBAC Graph & Permissions
          </h2>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Relationship-based authorization graph ({relationships.length} active relations in SpiceDB)
          </span>
        </div>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="btn-primary"
          style={{ fontSize: '0.8rem', padding: '8px 14px' }}
        >
          <Plus size={15} />
          {showAddForm ? 'Cancel' : 'Grant New Relationship'}
        </button>
      </div>

      {/* Grant Relationship Form */}
      {showAddForm && (
        <form
          onSubmit={handleCreate}
          className="glass-panel"
          style={{ padding: '20px', marginBottom: '20px', background: 'rgba(15, 23, 42, 0.95)', border: '1px solid var(--primary)' }}
        >
          <h3 style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Shield size={16} color="var(--primary)" />
            Grant Relationship Tuple (User ➔ Resource)
          </h3>

          {error && (
            <div style={{ color: 'var(--color-deny)', fontSize: '0.8rem', marginBottom: '12px' }}>
              {error}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '14px' }}>
            {/* Subject Type & ID */}
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Subject Type
              </label>
              <select
                value={subjectType}
                onChange={(e) => setSubjectType(e.target.value)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
              >
                <option value="user">user</option>
                <option value="organization">organization</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Subject / Username *
              </label>
              <input
                type="text"
                placeholder="e.g. alice, bob, charlie"
                value={subjectId}
                onChange={(e) => setSubjectId(e.target.value)}
                className="mono"
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
                required
              />
            </div>

            {/* Relation */}
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Relation (Role in Graph) *
              </label>
              <select
                value={relation}
                onChange={(e) => setRelation(e.target.value)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--primary)', color: '#fff', fontSize: '0.85rem' }}
              >
                <option value="owner">owner (full view + edit rights)</option>
                <option value="editor">editor (view + edit rights)</option>
                <option value="viewer">viewer (view only)</option>
                <option value="member">member (organization membership)</option>
              </select>
            </div>

            {/* Resource Type & ID */}
            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Resource Type *
              </label>
              <select
                value={resourceType}
                onChange={(e) => setResourceType(e.target.value)}
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
              >
                <option value="document">document</option>
                <option value="organization">organization</option>
                <option value="workspace">workspace</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                Resource ID *
              </label>
              <input
                type="text"
                placeholder="e.g. doc_1, doc_confidential"
                value={resourceId}
                onChange={(e) => setResourceId(e.target.value)}
                className="mono"
                style={{ width: '100%', padding: '8px 10px', borderRadius: '6px', background: '#0b0f17', border: '1px solid var(--card-border)', color: '#fff', fontSize: '0.85rem' }}
                required
              />
            </div>
          </div>

          {/* Tuple Preview Banner */}
          <div style={{ background: 'rgba(0, 0, 0, 0.4)', padding: '10px 14px', borderRadius: '6px', marginBottom: '14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>SpiceDB Tuple Preview:</span>
            <span className="mono" style={{ fontSize: '0.85rem', color: '#a5b4fc', fontWeight: 600 }}>
              {resourceType}:{resourceId}#{relation}@{subjectType}:{subjectId}
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="tab-btn"
              style={{ border: '1px solid var(--card-border)' }}
            >
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? 'Writing to SpiceDB...' : 'Write Relationship'}
            </button>
          </div>
        </form>
      )}

      {/* Two-Column Section: Left = User Access Inspector, Right = Active Relationships Graph */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        {/* User Access Inspector Card */}
        <div className="glass-panel" style={{ padding: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <UserCheck size={18} color="var(--color-allow)" />
              <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>
                User Resource Access Inspector
              </h3>
            </div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>SpiceDB CheckPermission</span>
          </div>

          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '12px' }}>
            Select a subject to instantly see what documents and resources they are authorized to access.
          </p>

          {/* User selector chips */}
          <div style={{ display: 'flex', gap: '6px', marginBottom: '14px', flexWrap: 'wrap' }}>
            {['user:alice', 'user:bob', 'user:charlie', 'user:admin', 'user:attacker'].map((u) => (
              <button
                key={u}
                onClick={() => setInspectUser(u)}
                className="tab-btn"
                style={{
                  padding: '4px 10px',
                  fontSize: '0.75rem',
                  background: inspectUser === u ? 'rgba(99, 102, 241, 0.25)' : 'rgba(255, 255, 255, 0.05)',
                  border: inspectUser === u ? '1px solid var(--primary)' : '1px solid var(--card-border)',
                  color: inspectUser === u ? '#fff' : 'var(--text-muted)',
                  fontWeight: inspectUser === u ? 600 : 400,
                }}
              >
                {u}
              </button>
            ))}
          </div>

          {/* Access Results List */}
          {inspectLoading ? (
            <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
              Checking SpiceDB permissions...
            </div>
          ) : userAccess.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '20px', color: 'var(--text-dim)', fontSize: '0.8rem' }}>
              No document resources found for {inspectUser}.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '280px', overflowY: 'auto' }}>
              {userAccess.map((acc) => {
                const hasView = acc.permissions.view;
                const hasEdit = acc.permissions.edit;
                const isNarrowed = acc.permissions.narrow_view;

                return (
                  <div
                    key={acc.resource}
                    style={{
                      background: 'rgba(0, 0, 0, 0.3)',
                      border: '1px solid var(--card-border)',
                      borderRadius: '6px',
                      padding: '10px 12px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <FileText size={14} color="var(--primary)" />
                        <span className="mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: '#fff' }}>
                          {acc.resource}
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: '6px', marginTop: '4px' }}>
                        {acc.relations.length > 0 ? (
                          acc.relations.map((r) => (
                            <span
                              key={r}
                              style={{
                                fontSize: '0.68rem',
                                background: 'rgba(99, 102, 241, 0.15)',
                                color: '#a5b4fc',
                                padding: '1px 5px',
                                borderRadius: '4px',
                              }}
                            >
                              role: {r}
                            </span>
                          ))
                        ) : (
                          <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>No direct relation</span>
                        )}
                        {isNarrowed && (
                          <span style={{ fontSize: '0.68rem', background: 'rgba(234, 179, 8, 0.2)', color: '#facc15', padding: '1px 5px', borderRadius: '4px', fontWeight: 600 }}>
                            Narrowed Access
                          </span>
                        )}
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                      <span
                        style={{
                          fontSize: '0.72rem',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                          background: hasEdit
                            ? 'rgba(34, 197, 94, 0.15)'
                            : hasView
                            ? 'rgba(56, 189, 248, 0.15)'
                            : 'rgba(239, 68, 68, 0.15)',
                          color: hasEdit
                            ? 'var(--color-allow)'
                            : hasView
                            ? '#38bdf8'
                            : 'var(--color-deny)',
                          fontWeight: 600,
                        }}
                      >
                        {hasEdit ? (
                          <>
                            <CheckCircle size={12} /> View + Edit
                          </>
                        ) : hasView ? (
                          <>
                            <CheckCircle size={12} /> View Only
                          </>
                        ) : (
                          <>
                            <XCircle size={12} /> Denied
                          </>
                        )}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Quick Schema Reference Card */}
        <div className="glass-panel" style={{ padding: '18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
            <Shield size={18} color="var(--primary)" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>
              ReBAC Zed Schema Rules
            </h3>
          </div>

          <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '12px' }}>
            Permissions compiled in SpiceDB (<code className="mono">schema.zed</code>) with closed-loop subtraction:
          </p>

          <div style={{ background: '#0b0f17', border: '1px solid var(--card-border)', borderRadius: '6px', padding: '12px', fontSize: '0.75rem', fontFamily: 'monospace', color: '#a5b4fc', lineHeight: 1.6 }}>
            <div><span style={{ color: '#f472b6' }}>definition</span> <span style={{ color: '#38bdf8' }}>document</span> &#123;</div>
            <div style={{ paddingLeft: '12px', color: 'var(--text-dim)' }}>relation owner: user</div>
            <div style={{ paddingLeft: '12px', color: 'var(--text-dim)' }}>relation editor: user</div>
            <div style={{ paddingLeft: '12px', color: 'var(--text-dim)' }}>relation viewer: user | organization#member</div>
            <div style={{ paddingLeft: '12px', color: '#facc15' }}>relation restricted_subject: user</div>
            <div style={{ paddingLeft: '12px', color: '#34d399', marginTop: '6px' }}>permission edit = (owner + editor) - restricted_subject</div>
            <div style={{ paddingLeft: '12px', color: '#34d399' }}>permission view = (owner + editor + viewer) - restricted_subject</div>
            <div style={{ paddingLeft: '12px', color: '#fb923c' }}>permission narrow_view = viewer & restricted_subject</div>
            <div>&#125;</div>
          </div>
        </div>
      </div>

      {/* Relationships Table */}
      <div className="glass-panel" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '14px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--card-border)', flexWrap: 'wrap', gap: '10px' }}>
          <span style={{ fontSize: '0.88rem', fontWeight: 600 }}>Active SpiceDB Relationship Tuples</span>
          <div style={{ position: 'relative', minWidth: '220px' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '9px', color: 'var(--text-dim)' }} />
            <input
              type="text"
              placeholder="Search tuples, users, or docs..."
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.target.value)}
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

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Resource</th>
                <th>Relation</th>
                <th>Subject (User / Org)</th>
                <th>Full Tuple</th>
                <th style={{ width: '80px' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredRels.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '28px', color: 'var(--text-dim)' }}>
                    {loading ? 'Fetching relationships from SpiceDB...' : 'No relationships match the filter.'}
                  </td>
                </tr>
              ) : (
                filteredRels.map((rel) => (
                  <tr key={rel.tuple}>
                    <td>
                      <span className="mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: '#38bdf8' }}>
                        {rel.resource_type}:{rel.resource_id}
                      </span>
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          background: rel.relation === 'restricted_subject'
                            ? 'rgba(234, 179, 8, 0.2)'
                            : 'rgba(99, 102, 241, 0.15)',
                          color: rel.relation === 'restricted_subject' ? '#facc15' : '#a5b4fc',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontWeight: 600,
                        }}
                      >
                        {rel.relation}
                      </span>
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-main)' }}>
                        {rel.subject_type}:{rel.subject_id}
                      </span>
                    </td>
                    <td>
                      <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                        {rel.tuple}
                      </span>
                    </td>
                    <td>
                      <button
                        onClick={() => handleDelete(rel)}
                        className="btn-danger"
                        style={{ padding: '4px 8px' }}
                        title="Delete from SpiceDB"
                      >
                        <Trash2 size={13} />
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

export default RebacGraphManager;
