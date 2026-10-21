export type SubjectId = 'user:alice' | 'user:bob' | 'user:charlie' | 'user:darth';

export interface SimulatorUser {
  id: SubjectId;
  name: string;
  role: string;
  department: string;
  avatarColor: string;
  initials: string;
}

export interface RequestRecord {
  id: string;
  timestamp: string;
  user: SubjectId;
  method: string;
  endpoint: string;
  clientIp: string;
  status: number;
  decision: 'allow' | 'step_up' | 'narrow' | 'deny';
  trustScore?: number;
  anomalyScore?: number;
  latencyMs: number;
  responseBody: string;
  reasons?: string[];
}

export interface RuntimeParameters {
  anomaly_weight: number;
  half_life_seconds: number;
  narrow_band_threshold: number;
  step_up_band_threshold: number;
  narrow_ttl_seconds: number;
}
