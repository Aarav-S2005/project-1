import type {
  AuditRecord,
  ClosedLoopRestriction,
  MiddlewareConfig,
  RebacRelationship,
  RouteConfig,
  UpstreamConfig,
  UserAccessInfo,
  UserTrustProfile,
} from './types';

const CONTROL_BASE = 'http://localhost:3002/api/v1';
const DATA_BASE = 'http://localhost:3003';

// Upstreams CRUD
export async function fetchUpstreams(): Promise<UpstreamConfig[]> {
  const res = await fetch(`${CONTROL_BASE}/upstreams`);
  if (!res.ok) throw new Error('Failed to fetch upstreams from MongoDB');
  return res.json();
}

export async function createUpstream(upstream: UpstreamConfig): Promise<UpstreamConfig> {
  const res = await fetch(`${CONTROL_BASE}/upstreams`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(upstream),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create upstream' }));
    throw new Error(err.detail || 'Failed to create upstream');
  }
  return res.json();
}

export async function deleteUpstream(id: string): Promise<void> {
  const res = await fetch(`${CONTROL_BASE}/upstreams/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete upstream '${id}'`);
}

// Routes CRUD
export async function fetchRoutes(): Promise<RouteConfig[]> {
  const res = await fetch(`${CONTROL_BASE}/routes`);
  if (!res.ok) throw new Error('Failed to fetch routes from MongoDB');
  return res.json();
}

export async function createRoute(route: RouteConfig): Promise<RouteConfig> {
  const res = await fetch(`${CONTROL_BASE}/routes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(route),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create route' }));
    throw new Error(err.detail || 'Failed to create route');
  }
  return res.json();
}

export async function deleteRoute(id: string): Promise<void> {
  const res = await fetch(`${CONTROL_BASE}/routes/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete route '${id}'`);
}

// Middlewares CRUD
export async function fetchMiddlewares(): Promise<MiddlewareConfig[]> {
  const res = await fetch(`${CONTROL_BASE}/middlewares`);
  if (!res.ok) throw new Error('Failed to fetch middlewares from MongoDB');
  return res.json();
}

export async function createMiddleware(mw: MiddlewareConfig): Promise<MiddlewareConfig> {
  const res = await fetch(`${CONTROL_BASE}/middlewares`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(mw),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create middleware' }));
    throw new Error(err.detail || 'Failed to create middleware');
  }
  return res.json();
}

export async function updateMiddleware(id: string, mw: MiddlewareConfig): Promise<MiddlewareConfig> {
  const res = await fetch(`${CONTROL_BASE}/middlewares/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(mw),
  });
  if (!res.ok) throw new Error(`Failed to update middleware '${id}'`);
  return res.json();
}

export async function deleteMiddleware(id: string): Promise<void> {
  const res = await fetch(`${CONTROL_BASE}/middlewares/${id}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`Failed to delete middleware '${id}'`);
}

// Audit Logs
export async function fetchAuditLogs(params?: {
  session_id?: string;
  subject_id?: string;
  decision?: string;
  limit?: number;
  skip?: number;
}): Promise<{ total: number; records: AuditRecord[] }> {
  const query = new URLSearchParams();
  if (params?.session_id) query.set('session_id', params.session_id);
  if (params?.subject_id) query.set('subject_id', params.subject_id);
  if (params?.decision) query.set('decision', params.decision);
  if (params?.limit) query.set('limit', params.limit.toString());
  if (params?.skip) query.set('skip', params.skip.toString());

  const res = await fetch(`${CONTROL_BASE}/audit/logs?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch audit logs');
  return res.json();
}

// Closed-Loop Restrictions
export async function fetchClosedLoopRestrictions(): Promise<ClosedLoopRestriction[]> {
  const res = await fetch(`${CONTROL_BASE}/closed-loop/restrictions`);
  if (!res.ok) throw new Error('Failed to fetch restrictions');
  return res.json();
}

export async function revokeRestriction(resource: string, subject: string): Promise<void> {
  const res = await fetch(`${CONTROL_BASE}/closed-loop/revoke`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resource, subject }),
  });
  if (!res.ok) throw new Error('Failed to revoke restriction');
}

// Test / Ping & Simulation
export async function testGatewayRequest(options: {
  path: string;
  method: string;
  subject?: string;
}): Promise<{ status: number; headers: Record<string, string>; data: any }> {
  return sendSimulatedRequest(options);
}

export async function sendSimulatedRequest(options: {
  path: string;
  method: string;
  subject?: string;
  sessionId?: string;
}): Promise<{ status: number; headers: Record<string, string>; data: any }> {
  const headers: Record<string, string> = {};
  if (options.subject) headers['X-Subject'] = options.subject;
  if (options.sessionId) headers['X-Session-ID'] = options.sessionId;

  const res = await fetch(`${DATA_BASE}${options.path}`, {
    method: options.method,
    headers,
  });

  const responseHeaders: Record<string, string> = {};
  res.headers.forEach((val, key) => {
    responseHeaders[key.toLowerCase()] = val;
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    data = await res.text();
  }

  return { status: res.status, headers: responseHeaders, data };
}

// ReBAC Graph Relationships & Access
export async function fetchRebacRelationships(params?: {
  resource_type?: string;
  subject_id?: string;
}): Promise<RebacRelationship[]> {
  const query = new URLSearchParams();
  if (params?.resource_type) query.set('resource_type', params.resource_type);
  if (params?.subject_id) query.set('subject_id', params.subject_id);

  const res = await fetch(`${CONTROL_BASE}/rebac/relationships?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch SpiceDB relationships');
  return res.json();
}

export async function createRebacRelationship(rel: {
  resource_type: string;
  resource_id: string;
  relation: string;
  subject_type: string;
  subject_id: string;
}): Promise<{ status: string; tuple: string }> {
  const res = await fetch(`${CONTROL_BASE}/rebac/relationships`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rel),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create relationship' }));
    throw new Error(err.detail || 'Failed to create relationship');
  }
  return res.json();
}

export async function deleteRebacRelationship(params: {
  resource_type: string;
  resource_id: string;
  relation: string;
  subject_type: string;
  subject_id: string;
}): Promise<void> {
  const query = new URLSearchParams(params);
  const res = await fetch(`${CONTROL_BASE}/rebac/relationships?${query.toString()}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error('Failed to delete relationship');
}

export async function checkRebacPermission(payload: {
  resource_type: string;
  resource_id: string;
  permission: string;
  subject_type: string;
  subject_id: string;
}): Promise<{ allowed: boolean; resource: string; permission: string; subject: string }> {
  const res = await fetch(`${CONTROL_BASE}/rebac/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to check permission in SpiceDB');
  return res.json();
}

export async function fetchUserAccess(subjectId: string): Promise<UserAccessInfo[]> {
  const res = await fetch(`${CONTROL_BASE}/rebac/user-access/${encodeURIComponent(subjectId)}`);
  if (!res.ok) throw new Error(`Failed to fetch access rights for ${subjectId}`);
  return res.json();
}

// User Trust Scores & Request History
export async function fetchUsersTrustScores(): Promise<UserTrustProfile[]> {
  const res = await fetch(`${CONTROL_BASE}/users/trust-scores`);
  if (!res.ok) throw new Error('Failed to fetch user trust scores');
  return res.json();
}

export async function fetchUserRequestHistory(subjectId: string, limit = 50): Promise<AuditRecord[]> {
  const res = await fetch(`${CONTROL_BASE}/users/${encodeURIComponent(subjectId)}/history?limit=${limit}`);
  if (!res.ok) throw new Error(`Failed to fetch history for ${subjectId}`);
  return res.json();
}

export async function resetUserTrust(subjectId: string): Promise<void> {
  const res = await fetch(`${CONTROL_BASE}/users/${encodeURIComponent(subjectId)}/reset-trust`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to reset trust score for ${subjectId}`);
}

// Runtime Trust Parameters (Redis)
export async function fetchRuntimeParameters(): Promise<import('./types').RuntimeParameters> {
  const res = await fetch(`${CONTROL_BASE}/trust/parameters`);
  if (!res.ok) throw new Error('Failed to fetch runtime trust parameters');
  return res.json();
}

export async function updateRuntimeParameters(params: import('./types').RuntimeParameters): Promise<void> {
  const res = await fetch(`${CONTROL_BASE}/trust/parameters`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  });
  if (!res.ok) throw new Error('Failed to update runtime trust parameters');
}

export async function setUserTrustScore(subjectId: string, score: number): Promise<void> {
  const res = await fetch(`${CONTROL_BASE}/users/${encodeURIComponent(subjectId)}/set-trust`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ score }),
  });
  if (!res.ok) throw new Error(`Failed to set trust score for ${subjectId}`);
}

export async function resetAllTrustAndAudit(
  targetScore: number = 1.0
): Promise<{ cleared_audit_records: number; message: string }> {
  const res = await fetch(`${CONTROL_BASE}/users/reset-all`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_score: targetScore, clear_audit: true }),
  });
  if (!res.ok) throw new Error('Failed to reset all users and clear audit logs');
  return res.json();
}


