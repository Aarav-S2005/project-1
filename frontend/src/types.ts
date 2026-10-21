export type DecisionAction = 'allow' | 'narrow' | 'step_up' | 'deny';

export interface AuditRecord {
  id?: string;
  _id?: string;
  request_id: string;
  session_id: string;
  subject_id: string;
  client_ip: string;
  route_id: string;
  resource: string;
  permission: string;
  trust_score_before: number;
  trust_score_after: number;
  decision: DecisionAction;
  decision_reason: string;
  features: Record<string, number>;
  shap_attributions: Record<string, number>;
  closed_loop_feedback?: {
    action: string;
    relation_tuple: string;
    ttl_seconds: number;
    created_at: string;
    expires_at: string;
  };
  latency_ms: number;
  timestamp: string;
}

export interface ClosedLoopRestriction {
  tuple: string;
  resource: string;
  subject: string;
  expires_at: string;
  ttl_remaining_seconds: number;
}

export interface UpstreamConfig {
  id: string;
  name: string;
  target_url: string;
  timeout_ms: number;
  health_check_path: string;
}

export interface RouteConfig {
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

export interface MiddlewareConfig {
  id: string;
  name: string;
  type: string;
  order: number;
  config: Record<string, any>;
  is_active: boolean;
}

export interface RebacRelationship {
  resource_type: string;
  resource_id: string;
  relation: string;
  subject_type: string;
  subject_id: string;
  tuple: string;
}

export interface UserAccessInfo {
  resource: string;
  resource_id: string;
  relations: string[];
  permissions: {
    view: boolean;
    edit: boolean;
    narrow_view: boolean;
  };
  effective_access: string;
}

export interface UserTrustProfile {
  subject_id: string;
  current_trust_score: number;
  latest_decision: DecisionAction;
  latest_reason: string;
  total_requests: number;
  anomalous_requests: number;
  is_restricted: boolean;
  last_seen: string;
  latest_shap: Record<string, number>;
}

export interface RuntimeParameters {
  half_life_seconds: number;
  anomaly_weight: number;
  narrow_band_threshold: number;
  step_up_band_threshold: number;
  narrow_ttl_seconds: number;
}

