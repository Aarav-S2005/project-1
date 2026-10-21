import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { RoutesManager } from './components/RoutesManager';
import { UpstreamsManager } from './components/UpstreamsManager';
import { MiddlewaresManager } from './components/MiddlewaresManager';
import { RebacGraphManager } from './components/RebacGraphManager';
import { UsersTrustManager } from './components/UsersTrustManager';
import { ClosedLoopViewer } from './components/ClosedLoopViewer';
import { AuditTable } from './components/AuditTable';
import { TrafficSimulatorModal } from './components/TrafficSimulatorModal';
import {
  fetchRoutes,
  fetchUpstreams,
  fetchMiddlewares,
  fetchClosedLoopRestrictions,
  fetchAuditLogs,
} from './api';
import type {
  RouteConfig,
  UpstreamConfig,
  MiddlewareConfig,
  ClosedLoopRestriction,
  AuditRecord,
} from './types';
import {
  Network,
  Server,
  Cpu,
  ShieldAlert,
  FileText,
  Send,
  Users,
  Share2,
} from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<
    'users' | 'rebac' | 'routes' | 'upstreams' | 'middlewares' | 'closed_loop' | 'audit'
  >('users');

  const [routes, setRoutes] = useState<RouteConfig[]>([]);
  const [upstreams, setUpstreams] = useState<UpstreamConfig[]>([]);
  const [middlewares, setMiddlewares] = useState<MiddlewareConfig[]>([]);
  const [restrictions, setRestrictions] = useState<ClosedLoopRestriction[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditRecord[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);

  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [simulatorOpen, setSimulatorOpen] = useState(false);
  const [auditFilterDecision, setAuditFilterDecision] = useState('ALL');
  const [auditSearchQuery, setAuditSearchQuery] = useState('');

  const loadData = useCallback(async () => {
    try {
      const [routesData, upstreamsData, middlewaresData, restrictionsData, logsData] = await Promise.all([
        fetchRoutes().catch(() => []),
        fetchUpstreams().catch(() => []),
        fetchMiddlewares().catch(() => []),
        fetchClosedLoopRestrictions().catch(() => []),
        fetchAuditLogs({
          decision: auditFilterDecision === 'ALL' ? undefined : auditFilterDecision,
          limit: 100,
        }).catch(() => ({ total: 0, records: [] })),
      ]);

      setRoutes(routesData);
      setUpstreams(upstreamsData);
      setMiddlewares(middlewaresData);
      setRestrictions(restrictionsData);
      setAuditLogs(logsData.records);
      setAuditTotal(logsData.total);
      setLastUpdated(new Date());
    } catch (err) {
      console.warn('Dashboard data refresh encountered an error:', err);
    }
  }, [auditFilterDecision]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Periodic polling every 4 seconds
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      loadData();
    }, 4000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadData]);

  return (
    <div className="container">
      {/* Top Admin Header */}
      <Header
        autoRefresh={autoRefresh}
        onToggleAutoRefresh={() => setAutoRefresh(!autoRefresh)}
        onManualRefresh={loadData}
        lastUpdated={lastUpdated}
      />

      {/* Navigation Tabs & Quick Test Trigger */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '20px',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div className="nav-tabs" style={{ flexWrap: 'wrap' }}>
          {/* 1. Users & Trust Scores Tab */}
          <button
            onClick={() => setActiveTab('users')}
            className={`tab-btn ${activeTab === 'users' ? 'active' : ''}`}
          >
            <Users size={16} />
            Users & Trust
          </button>

          {/* 2. ReBAC Graph & Permissions Tab */}
          <button
            onClick={() => setActiveTab('rebac')}
            className={`tab-btn ${activeTab === 'rebac' ? 'active' : ''}`}
          >
            <Share2 size={16} />
            ReBAC Graph
          </button>

          {/* 3. Routes Tab */}
          <button
            onClick={() => setActiveTab('routes')}
            className={`tab-btn ${activeTab === 'routes' ? 'active' : ''}`}
          >
            <Network size={16} />
            Routes
            <span
              style={{
                background: 'rgba(255, 255, 255, 0.15)',
                fontSize: '0.72rem',
                padding: '1px 6px',
                borderRadius: '10px',
                fontWeight: 600,
              }}
            >
              {routes.length}
            </span>
          </button>

          {/* 4. Upstreams Tab */}
          <button
            onClick={() => setActiveTab('upstreams')}
            className={`tab-btn ${activeTab === 'upstreams' ? 'active' : ''}`}
          >
            <Server size={16} />
            Upstreams
            <span
              style={{
                background: 'rgba(255, 255, 255, 0.15)',
                fontSize: '0.72rem',
                padding: '1px 6px',
                borderRadius: '10px',
                fontWeight: 600,
              }}
            >
              {upstreams.length}
            </span>
          </button>

          {/* 5. Middlewares Tab */}
          <button
            onClick={() => setActiveTab('middlewares')}
            className={`tab-btn ${activeTab === 'middlewares' ? 'active' : ''}`}
          >
            <Cpu size={16} />
            Middlewares
            <span
              style={{
                background: 'rgba(255, 255, 255, 0.15)',
                fontSize: '0.72rem',
                padding: '1px 6px',
                borderRadius: '10px',
                fontWeight: 600,
              }}
            >
              {middlewares.length}
            </span>
          </button>

          {/* 6. Active Restrictions Tab */}
          <button
            onClick={() => setActiveTab('closed_loop')}
            className={`tab-btn ${activeTab === 'closed_loop' ? 'active' : ''}`}
          >
            <ShieldAlert size={16} />
            Active Restrictions
            {restrictions.length > 0 ? (
              <span
                style={{
                  background: 'var(--color-narrow)',
                  color: '#000',
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  padding: '1px 6px',
                  borderRadius: '10px',
                }}
              >
                {restrictions.length}
              </span>
            ) : (
              <span
                style={{
                  background: 'rgba(255, 255, 255, 0.1)',
                  fontSize: '0.72rem',
                  padding: '1px 6px',
                  borderRadius: '10px',
                }}
              >
                0
              </span>
            )}
          </button>

          {/* 7. Audit Logs Tab */}
          <button
            onClick={() => setActiveTab('audit')}
            className={`tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
          >
            <FileText size={16} />
            Audit Logs
            {auditTotal > 0 && (
              <span
                style={{
                  background: 'rgba(255, 255, 255, 0.15)',
                  fontSize: '0.72rem',
                  padding: '1px 6px',
                  borderRadius: '10px',
                }}
              >
                {auditTotal}
              </span>
            )}
          </button>
        </div>

        {/* Quick Test Request Trigger */}
        <button
          onClick={() => setSimulatorOpen(true)}
          className="tab-btn"
          style={{
            background: 'rgba(99, 102, 241, 0.2)',
            border: '1px solid var(--primary)',
            color: '#a5b4fc',
            fontSize: '0.82rem',
            padding: '7px 14px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          <Send size={14} />
          Send Test Request
        </button>
      </div>

      {/* Main Tab Content */}
      <main>
        {activeTab === 'users' && <UsersTrustManager />}

        {activeTab === 'rebac' && <RebacGraphManager />}

        {activeTab === 'routes' && (
          <RoutesManager
            routes={routes}
            upstreams={upstreams}
            onRefresh={loadData}
          />
        )}

        {activeTab === 'upstreams' && (
          <UpstreamsManager
            upstreams={upstreams}
            onRefresh={loadData}
          />
        )}

        {activeTab === 'middlewares' && (
          <MiddlewaresManager
            middlewares={middlewares}
            onRefresh={loadData}
          />
        )}

        {activeTab === 'closed_loop' && (
          <ClosedLoopViewer
            restrictions={restrictions}
            onRefresh={loadData}
          />
        )}

        {activeTab === 'audit' && (
          <AuditTable
            records={auditLogs}
            total={auditTotal}
            selectedDecision={auditFilterDecision}
            onSelectDecision={setAuditFilterDecision}
            searchQuery={auditSearchQuery}
            onSearchChange={setAuditSearchQuery}
          />
        )}
      </main>

      {/* Test Request Modal */}
      <TrafficSimulatorModal
        isOpen={simulatorOpen}
        onClose={() => setSimulatorOpen(false)}
        onRefreshDashboard={loadData}
      />
    </div>
  );
};

export default App;
