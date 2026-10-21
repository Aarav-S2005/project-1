/**
 * Automated Gateway Registration Script
 * Registers demo backend microservices and ReBAC tuples with the Control Plane (Port 3002).
 */

export interface UpstreamRegistration {
  id: string;
  name: string;
  target_url: string;
  timeout_ms: number;
  health_check_path: string;
}

export interface RouteRegistration {
  id: string;
  upstream_id: string;
  path_prefix: string;
  methods: string[];
  strip_path: boolean;
  auth_required: boolean;
  resource_type: string;
  resource_id_extractor: string;
  permission_mapping: Record<string, string>;
}

export interface RebacTupleRegistration {
  resource_type: string;
  resource_id: string;
  relation: string;
  subject_type: string;
  subject_id: string;
}

const UPSTREAM_HOST = process.env.UPSTREAM_HOST || 'localhost';

export const DEMO_UPSTREAMS: UpstreamRegistration[] = [
  {
    id: 'upstream_users',
    name: 'Users Microservice',
    target_url: `http://${UPSTREAM_HOST}:4010`,
    timeout_ms: 5000,
    health_check_path: '/health',
  },
  {
    id: 'upstream_documents',
    name: 'Documents Microservice',
    target_url: `http://${UPSTREAM_HOST}:4011`,
    timeout_ms: 5000,
    health_check_path: '/health',
  },
  {
    id: 'upstream_payroll',
    name: 'Payroll Microservice',
    target_url: `http://${UPSTREAM_HOST}:4012`,
    timeout_ms: 5000,
    health_check_path: '/health',
  },
  {
    id: 'upstream_admin',
    name: 'Admin Microservice',
    target_url: `http://${UPSTREAM_HOST}:4013`,
    timeout_ms: 5000,
    health_check_path: '/health',
  },
];


export const DEMO_ROUTES: RouteRegistration[] = [
  {
    id: 'route_users',
    upstream_id: 'upstream_users',
    path_prefix: '/api/v1/users',
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    strip_path: false,
    auth_required: true,
    resource_type: 'document',
    resource_id_extractor: 'path_param:id',
    permission_mapping: {
      GET: 'view',
      POST: 'edit',
      PUT: 'edit',
      DELETE: 'edit',
    },
  },
  {
    id: 'route_documents',
    upstream_id: 'upstream_documents',
    path_prefix: '/api/v1/documents',
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    strip_path: false,
    auth_required: true,
    resource_type: 'document',
    resource_id_extractor: 'path_param:id',
    permission_mapping: {
      GET: 'view',
      POST: 'edit',
      PUT: 'edit',
      DELETE: 'edit',
    },
  },
  {
    id: 'route_payroll',
    upstream_id: 'upstream_payroll',
    path_prefix: '/api/v1/payroll',
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    strip_path: false,
    auth_required: true,
    resource_type: 'document',
    resource_id_extractor: 'path_param:id',
    permission_mapping: {
      GET: 'view',
      POST: 'edit',
      PUT: 'edit',
      DELETE: 'edit',
    },
  },
  {
    id: 'route_admin',
    upstream_id: 'upstream_admin',
    path_prefix: '/api/v1/admin',
    methods: ['GET', 'POST', 'PUT', 'DELETE'],
    strip_path: false,
    auth_required: true,
    resource_type: 'document',
    resource_id_extractor: 'path_param:id',
    permission_mapping: {
      GET: 'view',
      POST: 'edit',
      PUT: 'edit',
      DELETE: 'edit',
    },
  },
];

export const DEMO_REBAC_TUPLES: RebacTupleRegistration[] = [
  // Alice (Engineering Lead)
  { resource_type: 'document', resource_id: 'doc_eng_specs', relation: 'owner', subject_type: 'user', subject_id: 'alice' },
  { resource_type: 'document', resource_id: 'doc_eng_specs', relation: 'editor', subject_type: 'user', subject_id: 'alice' },
  { resource_type: 'document', resource_id: 'doc_eng_specs', relation: 'viewer', subject_type: 'user', subject_id: 'alice' },
  { resource_type: 'document', resource_id: 'doc_roadmap', relation: 'viewer', subject_type: 'user', subject_id: 'alice' },
  { resource_type: 'document', resource_id: 'pay_alice', relation: 'viewer', subject_type: 'user', subject_id: 'alice' },
  { resource_type: 'document', resource_id: 'me', relation: 'viewer', subject_type: 'user', subject_id: 'alice' },

  // Bob (Marketing Director)
  { resource_type: 'document', resource_id: 'doc_mkt_campaign', relation: 'owner', subject_type: 'user', subject_id: 'bob' },
  { resource_type: 'document', resource_id: 'doc_mkt_campaign', relation: 'editor', subject_type: 'user', subject_id: 'bob' },
  { resource_type: 'document', resource_id: 'doc_mkt_campaign', relation: 'viewer', subject_type: 'user', subject_id: 'bob' },
  { resource_type: 'document', resource_id: 'doc_roadmap', relation: 'viewer', subject_type: 'user', subject_id: 'bob' },
  { resource_type: 'document', resource_id: 'pay_bob', relation: 'viewer', subject_type: 'user', subject_id: 'bob' },
  { resource_type: 'document', resource_id: 'me', relation: 'viewer', subject_type: 'user', subject_id: 'bob' },

  // Charlie (Executive Admin)
  { resource_type: 'document', resource_id: 'doc_roadmap', relation: 'owner', subject_type: 'user', subject_id: 'charlie' },
  { resource_type: 'document', resource_id: 'doc_roadmap', relation: 'viewer', subject_type: 'user', subject_id: 'charlie' },
  { resource_type: 'document', resource_id: 'doc_exec_confidential', relation: 'owner', subject_type: 'user', subject_id: 'charlie' },
  { resource_type: 'document', resource_id: 'doc_exec_confidential', relation: 'editor', subject_type: 'user', subject_id: 'charlie' },
  { resource_type: 'document', resource_id: 'doc_exec_confidential', relation: 'viewer', subject_type: 'user', subject_id: 'charlie' },
  { resource_type: 'document', resource_id: 'pay_exec', relation: 'viewer', subject_type: 'user', subject_id: 'charlie' },
  { resource_type: 'document', resource_id: 'settings', relation: 'editor', subject_type: 'user', subject_id: 'charlie' },
  { resource_type: 'document', resource_id: 'settings', relation: 'viewer', subject_type: 'user', subject_id: 'charlie' },
  { resource_type: 'document', resource_id: 'me', relation: 'viewer', subject_type: 'user', subject_id: 'charlie' },
];

export async function registerWithControlPlane(controlPlaneUrl: string = 'http://localhost:3002') {
  console.log(`[Demo Register] Connecting to Control Plane at ${controlPlaneUrl}...`);

  // 1. Ensure SpiceDB Zed Schema is applied
  try {
    const schemaRes = await fetch(`${controlPlaneUrl}/api/v1/rebac/schema`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (schemaRes.ok) {
      console.log(`[SpiceDB] Zed schema verified and applied.`);
    } else {
      const errText = await schemaRes.text();
      console.warn(`[SpiceDB] Schema initialization warning: ${schemaRes.status} - ${errText}`);
    }
  } catch (err) {
    console.warn(`[SpiceDB] Could not apply schema via Control Plane:`, err);
  }

  // 2. Register Upstreams
  for (const upstream of DEMO_UPSTREAMS) {
    try {
      const res = await fetch(`${controlPlaneUrl}/api/v1/upstreams`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(upstream),
      });

      if (res.status === 201) {
        console.log(`[Upstream] Registered: ${upstream.id} -> ${upstream.target_url}`);
      } else if (res.status === 409) {
        await fetch(`${controlPlaneUrl}/api/v1/upstreams/${upstream.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(upstream),
        });
        console.log(`[Upstream] Updated: ${upstream.id}`);
      } else {
        const errText = await res.text();
        console.warn(`[Upstream] Unexpected response for ${upstream.id}: ${res.status} - ${errText}`);
      }
    } catch (err) {
      console.error(`[Upstream] Failed to register ${upstream.id}:`, err);
    }
  }

  // 2. Register Routes
  for (const route of DEMO_ROUTES) {
    try {
      const res = await fetch(`${controlPlaneUrl}/api/v1/routes`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(route),
      });

      if (res.status === 201) {
        console.log(`[Route] Registered: ${route.id} -> ${route.path_prefix}`);
      } else if (res.status === 409) {
        await fetch(`${controlPlaneUrl}/api/v1/routes/${route.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(route),
        });
        console.log(`[Route] Updated: ${route.id}`);
      } else {
        const errText = await res.text();
        console.warn(`[Route] Unexpected response for ${route.id}: ${res.status} - ${errText}`);
      }
    } catch (err) {
      console.error(`[Route] Failed to register ${route.id}:`, err);
    }
  }

  // 3. Register SpiceDB ReBAC Tuples
  let createdCount = 0;
  for (const tuple of DEMO_REBAC_TUPLES) {
    try {
      const res = await fetch(`${controlPlaneUrl}/api/v1/rebac/relationships`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tuple),
      });
      if (res.ok) {
        createdCount++;
      } else {
        const text = await res.text();
        console.warn(`[ReBAC] Failed to write tuple: ${tuple.resource_id}#${tuple.relation}@${tuple.subject_id}: ${text}`);
      }
    } catch (err) {
      console.error(`[ReBAC] Network error writing tuple:`, err);
    }
  }

  console.log(`[Demo Register] Completed! Wrote ${createdCount}/${DEMO_REBAC_TUPLES.length} ReBAC relationships.`);
  return { upstreams: DEMO_UPSTREAMS.length, routes: DEMO_ROUTES.length, rebac: createdCount };
}

// Allow direct CLI invocation
if (process.argv[1]?.endsWith('register.ts') || process.argv[1]?.endsWith('register.js')) {
  registerWithControlPlane().catch(console.error);
}
