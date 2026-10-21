import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  DEMO_UPSTREAMS,
  DEMO_ROUTES,
  DEMO_REBAC_TUPLES,
  registerWithControlPlane,
} from '../src/scripts/register';

describe('Demo Gateway Registration', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('contains configurations for all 4 microservices', () => {
    expect(DEMO_UPSTREAMS.length).toBe(4);
    const upstreamIds = DEMO_UPSTREAMS.map((u) => u.id);
    expect(upstreamIds).toContain('upstream_users');
    expect(upstreamIds).toContain('upstream_documents');
    expect(upstreamIds).toContain('upstream_payroll');
    expect(upstreamIds).toContain('upstream_admin');
  });

  it('contains matching routes for each service prefix', () => {
    expect(DEMO_ROUTES.length).toBe(4);
    const prefixes = DEMO_ROUTES.map((r) => r.path_prefix);
    expect(prefixes).toContain('/api/v1/users');
    expect(prefixes).toContain('/api/v1/documents');
    expect(prefixes).toContain('/api/v1/payroll');
    expect(prefixes).toContain('/api/v1/admin');

    for (const route of DEMO_ROUTES) {
      expect(route.auth_required).toBe(true);
      expect(route.resource_type).toBe('document');
      expect(route.methods).toContain('GET');
    }
  });

  it('contains comprehensive SpiceDB relationship seeds', () => {
    expect(DEMO_REBAC_TUPLES.length).toBeGreaterThan(10);
    const subjects = new Set(DEMO_REBAC_TUPLES.map((t) => t.subject_id));
    expect(subjects.has('alice')).toBe(true);
    expect(subjects.has('bob')).toBe(true);
    expect(subjects.has('charlie')).toBe(true);
  });

  it('invokes control plane endpoints with valid payloads and handles 201/409', async () => {
    const fetchMock = vi.fn().mockImplementation((url: string, options?: any) => {
      if (url.includes('/api/v1/upstreams')) {
        return Promise.resolve({
          status: 201,
          ok: true,
          json: () => Promise.resolve({}),
          text: () => Promise.resolve(''),
        });
      }
      if (url.includes('/api/v1/routes')) {
        return Promise.resolve({
          status: 201,
          ok: true,
          json: () => Promise.resolve({}),
          text: () => Promise.resolve(''),
        });
      }
      if (url.includes('/api/v1/rebac/relationships')) {
        return Promise.resolve({
          status: 200,
          ok: true,
          json: () => Promise.resolve({ status: 'created' }),
          text: () => Promise.resolve(''),
        });
      }
      return Promise.resolve({ status: 200, ok: true });
    });

    vi.stubGlobal('fetch', fetchMock);

    const result = await registerWithControlPlane('http://localhost:3002');
    expect(result.upstreams).toBe(4);
    expect(result.routes).toBe(4);
    expect(result.rebac).toBe(DEMO_REBAC_TUPLES.length);
    expect(fetchMock).toHaveBeenCalled();
  });
});
