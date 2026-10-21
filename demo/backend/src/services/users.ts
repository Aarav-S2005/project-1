import express, { Request, Response } from 'express';
import cors from 'cors';
import { dataStore } from '../db/dataStore';

export function createUsersApp() {
  const app = express();
  app.use(cors());
  app.use(express.json());

  // Helper to extract caller subject (e.g. "user:alice" -> "alice")
  function getCaller(req: Request): string | undefined {
    const authHeader = req.headers.authorization;
    if (authHeader && authHeader.startsWith('Bearer ')) {
      return authHeader.substring(7).trim();
    }
    const xSubject = req.headers['x-subject'];
    if (typeof xSubject === 'string' && xSubject.trim()) {
      return xSubject.trim();
    }
    return undefined;
  }

  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok', service: 'users', timestamp: new Date().toISOString() });
  });

  // Current authenticated user profile
  app.get('/api/v1/users/me', (req: Request, res: Response) => {
    const caller = getCaller(req);
    if (!caller) {
      return res.status(401).json({ error: 'Unauthorized: missing identity token or header' });
    }
    const user = dataStore.getUser(caller);
    if (!user) {
      return res.status(404).json({ error: `User '${caller}' not found` });
    }
    const { passwordHash, ...profile } = user;
    return res.json({ user: profile });
  });

  // List all users (directory)
  app.get('/api/v1/users', (_req: Request, res: Response) => {
    const users = dataStore.listUsers();
    res.json({ users });
  });

  // Get specific user
  app.get('/api/v1/users/:id', (req: Request, res: Response) => {
    const user = dataStore.getUser(req.params.id);
    if (!user) {
      return res.status(404).json({ error: `User '${req.params.id}' not found` });
    }
    const { passwordHash, ...profile } = user;
    return res.json({ user: profile });
  });

  return app;
}
