import express, { Request, Response } from 'express';
import cors from 'cors';
import { dataStore, DocumentRecord } from '../db/dataStore';

export function createDocumentsApp() {
  const app = express();
  app.use(cors());
  app.use(express.json());

  app.get('/health', (_req: Request, res: Response) => {
    res.json({ status: 'ok', service: 'documents', timestamp: new Date().toISOString() });
  });

  // List all documents
  app.get('/api/v1/documents', (_req: Request, res: Response) => {
    const documents = dataStore.listDocuments();
    res.json({ documents });
  });

  // Get specific document by ID
  app.get('/api/v1/documents/:id', (req: Request, res: Response) => {
    const doc = dataStore.getDocument(req.params.id);
    if (!doc) {
      return res.status(404).json({ error: `Document '${req.params.id}' not found` });
    }
    return res.json({ document: doc });
  });

  // Create or update a document
  app.post('/api/v1/documents', (req: Request, res: Response) => {
    const { id, title, owner, department, content } = req.body;
    if (!id || !title) {
      return res.status(400).json({ error: 'Fields "id" and "title" are required' });
    }
    const docRecord: DocumentRecord = {
      id,
      title,
      owner: owner || 'user:unknown',
      department: department || 'General',
      content: content || '',
      updatedAt: new Date().toISOString(),
    };
    dataStore.saveDocument(docRecord);
    return res.status(201).json({ message: 'Document saved', document: docRecord });
  });

  // Delete a document
  app.delete('/api/v1/documents/:id', (req: Request, res: Response) => {
    const deleted = dataStore.deleteDocument(req.params.id);
    if (!deleted) {
      return res.status(404).json({ error: `Document '${req.params.id}' not found` });
    }
    return res.json({ message: `Document '${req.params.id}' deleted` });
  });

  return app;
}
