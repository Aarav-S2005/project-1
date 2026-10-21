import { describe, it, expect, beforeAll, afterAll, beforeEach } from 'vitest';
import http from 'http';
import { AddressInfo } from 'net';
import { createUsersApp } from '../src/services/users';
import { createDocumentsApp } from '../src/services/documents';
import { createPayrollApp } from '../src/services/payroll';
import { createAdminApp } from '../src/services/admin';
import { dataStore } from '../src/db/dataStore';

describe('Demo Backend Microservices HTTP Tests', () => {
  let usersServer: http.Server;
  let docsServer: http.Server;
  let payrollServer: http.Server;
  let adminServer: http.Server;

  let usersUrl: string;
  let docsUrl: string;
  let payrollUrl: string;
  let adminUrl: string;

  beforeAll(async () => {
    await new Promise<void>((resolve) => {
      usersServer = createUsersApp().listen(0, () => {
        const port = (usersServer.address() as AddressInfo).port;
        usersUrl = `http://127.0.0.1:${port}`;
        resolve();
      });
    });

    await new Promise<void>((resolve) => {
      docsServer = createDocumentsApp().listen(0, () => {
        const port = (docsServer.address() as AddressInfo).port;
        docsUrl = `http://127.0.0.1:${port}`;
        resolve();
      });
    });

    await new Promise<void>((resolve) => {
      payrollServer = createPayrollApp().listen(0, () => {
        const port = (payrollServer.address() as AddressInfo).port;
        payrollUrl = `http://127.0.0.1:${port}`;
        resolve();
      });
    });

    await new Promise<void>((resolve) => {
      adminServer = createAdminApp().listen(0, () => {
        const port = (adminServer.address() as AddressInfo).port;
        adminUrl = `http://127.0.0.1:${port}`;
        resolve();
      });
    });
  });

  afterAll(async () => {
    await Promise.all([
      new Promise((res) => usersServer.close(res)),
      new Promise((res) => docsServer.close(res)),
      new Promise((res) => payrollServer.close(res)),
      new Promise((res) => adminServer.close(res)),
    ]);
  });

  beforeEach(() => {
    dataStore.reset();
  });

  describe('Users Service (:4010)', () => {
    it('returns health status', async () => {
      const res = await fetch(`${usersUrl}/health`);
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.status).toBe('ok');
      expect(data.service).toBe('users');
    });

    it('returns current user profile for authenticated caller', async () => {
      const res = await fetch(`${usersUrl}/api/v1/users/me`, {
        headers: { Authorization: 'Bearer user:alice' },
      });
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.user.id).toBe('alice');
      expect(data.user.name).toBe('Alice Vance');
      expect(data.user.department).toBe('Engineering');
    });

    it('returns 401 when missing identity', async () => {
      const res = await fetch(`${usersUrl}/api/v1/users/me`);
      expect(res.status).toBe(401);
    });

    it('lists directory of users', async () => {
      const res = await fetch(`${usersUrl}/api/v1/users`);
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.users.length).toBe(3);
    });

    it('returns specific user by id', async () => {
      const res = await fetch(`${usersUrl}/api/v1/users/bob`);
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.user.department).toBe('Marketing');
    });
  });

  describe('Documents Service (:4011)', () => {
    it('returns health status', async () => {
      const res = await fetch(`${docsUrl}/health`);
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.service).toBe('documents');
    });

    it('lists documents', async () => {
      const res = await fetch(`${docsUrl}/api/v1/documents`);
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.documents.length).toBe(4);
    });

    it('gets document by id', async () => {
      const res = await fetch(`${docsUrl}/api/v1/documents/doc_eng_specs`);
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.document.title).toContain('Zero-Trust Architecture Spec');
    });

    it('creates and deletes documents', async () => {
      const postRes = await fetch(`${docsUrl}/api/v1/documents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: 'doc_temp',
          title: 'Draft Document',
          owner: 'user:alice',
          content: 'Secret content',
        }),
      });
      expect(postRes.status).toBe(201);

      const delRes = await fetch(`${docsUrl}/api/v1/documents/doc_temp`, {
        method: 'DELETE',
      });
      expect(delRes.status).toBe(200);
    });
  });

  describe('Payroll Service (:4012)', () => {
    it('returns health status', async () => {
      const res = await fetch(`${payrollUrl}/health`);
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.service).toBe('payroll');
    });

    it('lists payroll records', async () => {
      const res = await fetch(`${payrollUrl}/api/v1/payroll`);
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.payroll.length).toBe(3);
    });

    it('gets individual payroll record', async () => {
      const res = await fetch(`${payrollUrl}/api/v1/payroll/pay_alice`);
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.payroll.annualSalary).toBe('$145,000');
    });
  });

  describe('Admin Service (:4013)', () => {
    it('returns health status', async () => {
      const res = await fetch(`${adminUrl}/health`);
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.service).toBe('admin');
    });

    it('gets admin settings and purges cache', async () => {
      const res = await fetch(`${adminUrl}/api/v1/admin/settings`);
      expect(res.status).toBe(200);
      const data = await res.json();
      expect(data.settings.cacheStatus).toBe('warm');

      const purgeRes = await fetch(`${adminUrl}/api/v1/admin/purge-cache`, { method: 'POST' });
      expect(purgeRes.status).toBe(200);

      const updated = await fetch(`${adminUrl}/api/v1/admin/settings`).then((r) => r.json());
      expect(updated.settings.cacheStatus).toBe('purged');
    });

    it('resets demo database', async () => {
      await fetch(`${adminUrl}/api/v1/admin/purge-cache`, { method: 'POST' });
      const resetRes = await fetch(`${adminUrl}/api/v1/admin/reset-demo`, { method: 'POST' });
      expect(resetRes.status).toBe(200);

      const resetData = await fetch(`${adminUrl}/api/v1/admin/settings`).then((r) => r.json());
      expect(resetData.settings.cacheStatus).toBe('warm');
    });
  });
});
