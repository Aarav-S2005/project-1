/**
 * In-memory transactional data store initialized with baseline business data.
 */

export interface UserRecord {
  id: string;
  username: string;
  passwordHash: string;
  name: string;
  role: 'user' | 'admin';
  department: string;
  team: string;
  email: string;
}

export interface DocumentRecord {
  id: string;
  title: string;
  owner: string;
  department: string;
  content: string;
  updatedAt: string;
}

export interface PayrollRecord {
  id: string;
  employeeId: string;
  name: string;
  department: string;
  annualSalary: string;
  bonus: string;
  disbursementStatus: 'paid' | 'pending';
}

export interface AdminSettings {
  maintenanceMode: boolean;
  activeTenants: string[];
  cacheStatus: 'warm' | 'purged';
  workerThreads: number;
}

const DEFAULT_USERS: Record<string, UserRecord> = {
  alice: {
    id: 'alice',
    username: 'alice',
    passwordHash: 'alice123',
    name: 'Alice Vance',
    role: 'user',
    department: 'Engineering',
    team: 'team:eng',
    email: 'alice@acme.corp',
  },
  bob: {
    id: 'bob',
    username: 'bob',
    passwordHash: 'bob123',
    name: 'Bob Stone',
    role: 'user',
    department: 'Marketing',
    team: 'team:mkt',
    email: 'bob@acme.corp',
  },
  charlie: {
    id: 'charlie',
    username: 'charlie',
    passwordHash: 'admin123',
    name: 'Charlie King',
    role: 'admin',
    department: 'Executive',
    team: 'team:admin',
    email: 'charlie@acme.corp',
  },
};

const DEFAULT_DOCUMENTS: Record<string, DocumentRecord> = {
  doc_eng_specs: {
    id: 'doc_eng_specs',
    title: 'Zero-Trust Architecture Spec',
    owner: 'user:alice',
    department: 'Engineering',
    content: 'Microservices proxy routing, token extraction, and ReBAC contracts.',
    updatedAt: new Date().toISOString(),
  },
  doc_mkt_campaign: {
    id: 'doc_mkt_campaign',
    title: 'Q4 Product Marketing Strategy',
    owner: 'user:bob',
    department: 'Marketing',
    content: 'Customer acquisition roadmap, social ad funnels, and marketing collateral.',
    updatedAt: new Date().toISOString(),
  },
  doc_roadmap: {
    id: 'doc_roadmap',
    title: '2026 Company Strategic Roadmap',
    owner: 'user:charlie',
    department: 'Corporate Strategy',
    content: 'Enterprise milestones, core product releases, and expansion plans.',
    updatedAt: new Date().toISOString(),
  },
  doc_exec_confidential: {
    id: 'doc_exec_confidential',
    title: 'Confidential M&A Acquisition Terms',
    owner: 'user:charlie',
    department: 'Executive Board',
    content: 'Strictly confidential executive board negotiations and financial terms.',
    updatedAt: new Date().toISOString(),
  },
};

const DEFAULT_PAYROLL: Record<string, PayrollRecord> = {
  pay_alice: {
    id: 'pay_alice',
    employeeId: 'user:alice',
    name: 'Alice Vance',
    department: 'Engineering',
    annualSalary: '$145,000',
    bonus: '$18,000',
    disbursementStatus: 'paid',
  },
  pay_bob: {
    id: 'pay_bob',
    employeeId: 'user:bob',
    name: 'Bob Stone',
    department: 'Marketing',
    annualSalary: '$118,000',
    bonus: '$12,500',
    disbursementStatus: 'paid',
  },
  pay_exec: {
    id: 'pay_exec',
    employeeId: 'user:charlie',
    name: 'Charlie King',
    department: 'Executive',
    annualSalary: '$240,000',
    bonus: '$60,000',
    disbursementStatus: 'paid',
  },
};

const DEFAULT_ADMIN: AdminSettings = {
  maintenanceMode: false,
  activeTenants: ['acme-corp', 'globex-corp', 'initech-subsidiary'],
  cacheStatus: 'warm',
  workerThreads: 8,
};

class DataStore {
  private users: Map<string, UserRecord> = new Map();
  private documents: Map<string, DocumentRecord> = new Map();
  private payroll: Map<string, PayrollRecord> = new Map();
  private admin: AdminSettings = { ...DEFAULT_ADMIN };

  constructor() {
    this.reset();
  }

  public reset(): void {
    this.users.clear();
    Object.values(DEFAULT_USERS).forEach((u) => this.users.set(u.id, { ...u }));

    this.documents.clear();
    Object.values(DEFAULT_DOCUMENTS).forEach((d) => this.documents.set(d.id, { ...d }));

    this.payroll.clear();
    Object.values(DEFAULT_PAYROLL).forEach((p) => this.payroll.set(p.id, { ...p }));

    this.admin = { ...DEFAULT_ADMIN, activeTenants: [...DEFAULT_ADMIN.activeTenants] };
  }

  // Users API
  public getUser(idOrUsername: string): UserRecord | undefined {
    const clean = idOrUsername.replace(/^user:/, '');
    return this.users.get(clean);
  }

  public listUsers(): UserRecord[] {
    return Array.from(this.users.values()).map(({ passwordHash, ...rest }) => ({
      ...rest,
      passwordHash: '***',
    }));
  }

  // Documents API
  public getDocument(id: string): DocumentRecord | undefined {
    return this.documents.get(id);
  }

  public listDocuments(): DocumentRecord[] {
    return Array.from(this.documents.values());
  }

  public saveDocument(doc: DocumentRecord): void {
    this.documents.set(doc.id, { ...doc, updatedAt: new Date().toISOString() });
  }

  public deleteDocument(id: string): boolean {
    return this.documents.delete(id);
  }

  // Payroll API
  public getPayroll(id: string): PayrollRecord | undefined {
    return this.payroll.get(id);
  }

  public listPayroll(): PayrollRecord[] {
    return Array.from(this.payroll.values());
  }

  // Admin API
  public getAdminSettings(): AdminSettings {
    return { ...this.admin };
  }

  public purgeCache(): void {
    this.admin.cacheStatus = 'purged';
  }

  public addTenant(tenant: string): void {
    if (!this.admin.activeTenants.includes(tenant)) {
      this.admin.activeTenants.push(tenant);
    }
  }
}

export const dataStore = new DataStore();
