import express, { Request, Response } from 'express';
import cors from 'cors';
import { dataStore } from '../db/dataStore';

export function createAdminApp() {
  const app = express();
  app.use(cors());
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok', service: 'admin', timestamp: new Date().toISOString() });
  });

  // Get administrative settings
  app.get('/api/v1/admin/settings', (_req: Request, res: Response) => {
    const settings = dataStore.getAdminSettings();
    res.json({ settings });
  });

  // Purge application cache
  app.post('/api/v1/admin/purge-cache', (_req: Request, res: Response) => {
    dataStore.purgeCache();
    res.json({ message: 'Application caches purged successfully', status: 'purged' });
  });

  // Add active tenant
  app.post('/api/v1/admin/tenants', (req: Request, res: Response) => {
    const { tenant } = req.body;
    if (!tenant || typeof tenant !== 'string') {
      return res.status(400).json({ error: 'Field "tenant" is required' });
    }
    dataStore.addTenant(tenant);
    return res.json({ message: `Tenant '${tenant}' registered`, settings: dataStore.getAdminSettings() });
  });

  // Reset entire demo data to original state
  app.post('/api/v1/admin/reset-demo', (_req: Request, res: Response) => {
    dataStore.reset();
    res.json({ message: 'Demo application data reset to initial seed state', status: 'ok' });
  });

  return app;
}
