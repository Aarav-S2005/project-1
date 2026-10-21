import { describe, it, expect, beforeEach } from 'vitest';
import { dataStore } from '../src/db/dataStore';

describe('Demo Backend DataStore', () => {
  beforeEach(() => {
    dataStore.reset();
  });

  describe('Users', () => {
    it('retrieves user by id or prefixed id', () => {
      const alice = dataStore.getUser('alice');
      expect(alice).toBeDefined();
      expect(alice?.name).toBe('Alice Vance');
      expect(alice?.department).toBe('Engineering');

      const alicePrefixed = dataStore.getUser('user:alice');
      expect(alicePrefixed).toEqual(alice);
    });

    it('returns undefined for non-existent user', () => {
      expect(dataStore.getUser('nonexistent')).toBeUndefined();
    });

    it('lists users masking password hashes', () => {
      const users = dataStore.listUsers();
      expect(users.length).toBe(3);
      for (const u of users) {
        expect(u.passwordHash).toBe('***');
      }
    });
  });

  describe('Documents', () => {
    it('retrieves existing document', () => {
      const doc = dataStore.getDocument('doc_eng_specs');
      expect(doc).toBeDefined();
      expect(doc?.department).toBe('Engineering');
      expect(doc?.owner).toBe('user:alice');
    });

    it('lists documents', () => {
      const docs = dataStore.listDocuments();
      expect(docs.length).toBe(4);
    });

    it('saves and deletes documents', () => {
      const newDoc = {
        id: 'doc_temp',
        title: 'Temporary Spec',
        owner: 'user:alice',
        department: 'Engineering',
        content: 'Testing temp content',
        updatedAt: new Date().toISOString(),
      };
      dataStore.saveDocument(newDoc);
      expect(dataStore.getDocument('doc_temp')?.title).toBe('Temporary Spec');

      const deleted = dataStore.deleteDocument('doc_temp');
      expect(deleted).toBe(true);
      expect(dataStore.getDocument('doc_temp')).toBeUndefined();
    });
  });

  describe('Payroll', () => {
    it('retrieves payroll record', () => {
      const pay = dataStore.getPayroll('pay_alice');
      expect(pay).toBeDefined();
      expect(pay?.employeeId).toBe('user:alice');
      expect(pay?.annualSalary).toBe('$145,000');
    });

    it('lists all payroll entries', () => {
      const allPay = dataStore.listPayroll();
      expect(allPay.length).toBe(3);
    });
  });

  describe('Admin Settings', () => {
    it('returns default admin settings and allows mutations', () => {
      const initial = dataStore.getAdminSettings();
      expect(initial.maintenanceMode).toBe(false);
      expect(initial.cacheStatus).toBe('warm');

      dataStore.purgeCache();
      expect(dataStore.getAdminSettings().cacheStatus).toBe('purged');

      dataStore.addTenant('new-corp');
      expect(dataStore.getAdminSettings().activeTenants).toContain('new-corp');
    });

    it('resets state properly', () => {
      dataStore.purgeCache();
      dataStore.addTenant('new-corp');
      dataStore.reset();

      const resetSettings = dataStore.getAdminSettings();
      expect(resetSettings.cacheStatus).toBe('warm');
      expect(resetSettings.activeTenants).not.toContain('new-corp');
    });
  });
});
