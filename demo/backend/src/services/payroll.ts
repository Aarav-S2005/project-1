import express, { Request, Response } from 'express';
import cors from 'cors';
import { dataStore } from '../db/dataStore';

export function createPayrollApp() {
  const app = express();
  app.use(cors());
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok', service: 'payroll', timestamp: new Date().toISOString() });
  });

  // List all payroll records
  app.get('/api/v1/payroll', (_req: Request, res: Response) => {
    const payroll = dataStore.listPayroll();
    res.json({ payroll });
  });

  // Get specific payroll record by ID
  app.get('/api/v1/payroll/:id', (req: Request, res: Response) => {
    const record = dataStore.getPayroll(req.params.id);
    if (!record) {
      return res.status(404).json({ error: `Payroll record '${req.params.id}' not found` });
    }
    return res.json({ payroll: record });
  });

  return app;
}
