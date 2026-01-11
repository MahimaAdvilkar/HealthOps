import React, { useEffect, useState } from 'react';
import { apiService, OpsSummary, Stats } from '../services/api';
import '../styles/Dashboard.css';

interface DashboardProps {
  onNavigate: (tab: 'referrals' | 'caregivers' | 'scheduler' | 'intake' | 'compliance' | 'journey') => void;
  onDataChanged: () => void;
  dataVersion: number;
}

const Dashboard: React.FC<DashboardProps> = ({ onNavigate, onDataChanged, dataVersion }) => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [ops, setOps] = useState<OpsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [intakeLoading, setIntakeLoading] = useState(false);
  const [intakeMessage, setIntakeMessage] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, [dataVersion]);

  const loadStats = async () => {
    try {
      const [statsResult] = await Promise.allSettled([apiService.getStats()]);

      if (statsResult.status === 'fulfilled') {
        setStats(statsResult.value);
      } else {
        console.error('Failed to load stats:', statsResult.reason);
      }

      const opsResult = await Promise.allSettled([apiService.getOpsSummary({ limit: 10 })]);
      if (opsResult[0].status === 'fulfilled') {
        setOps(opsResult[0].value);
      } else {
        console.error('Failed to load ops summary:', opsResult[0].reason);
      }
    } catch (err) {
      console.error('Failed to load stats:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSimulateIntake = async () => {
    try {
      setIntakeLoading(true);
      setIntakeMessage(null);

      const resp = await apiService.simulateIntake();
      setIntakeMessage(`New referral added: ${resp.referral.referral_id} (${resp.mode})`);

      // Refresh all tabs
      onDataChanged();
      onNavigate('referrals');
    } catch (e) {
      setIntakeMessage('Failed to add new referral');
      console.error(e);
    } finally {
      setIntakeLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading statistics...</div>;

  return (
    <div className="dashboard-wrapper">
      {ops && (
        <section className="dashboard-section">
          <div className="dashboard-title-row">
            <h2 className="dashboard-title">Operations Summary</h2>
            <div className="dashboard-actions">
              <button className="intake-btn secondary" onClick={() => onNavigate('intake')}>
                Upload PDFs (LandingAI)
              </button>
              <button className="intake-btn" onClick={handleSimulateIntake} disabled={intakeLoading}>
                {intakeLoading ? 'Adding…' : 'Simulate New Referral Intake'}
              </button>
            </div>
          </div>
          {intakeMessage && <div className="dashboard-message">{intakeMessage}</div>}
          <div className="dashboard-stats">
            <div className="stat-card clickable" onClick={() => onNavigate('referrals')}>
              <div className="stat-value">{ops.kpis.active_clients}</div>
              <div className="stat-label">Active Clients</div>
              <div className="stat-hint">Click to view</div>
            </div>
            <div className="stat-card clickable" onClick={() => onNavigate('referrals')}>
              <div className="stat-value">{ops.kpis.pending_scheduling}</div>
              <div className="stat-label">Pending Scheduling</div>
              <div className="stat-hint">Click to view</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{ops.kpis.urgent_pending}</div>
              <div className="stat-label">Urgent Pending</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{ops.kpis.leads_last_7d}</div>
              <div className="stat-label">Leads (Last 7d)</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{ops.kpis.paired_referrals}</div>
              <div className="stat-label">Paired Referrals</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{ops.kpis.available_caregivers ?? '—'}</div>
              <div className="stat-label">Caregivers Available</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{ops.kpis.unique_caregivers_paired}</div>
              <div className="stat-label">Caregivers Paired</div>
            </div>
          </div>

          {ops.priority_queue.length > 0 && (
            <div className="dashboard-funnel">
              <h3>Priority Queue (Top)</h3>
              <table className="funnel-table">
                <thead>
                  <tr>
                    <th>Referral</th>
                    <th>Priority</th>
                    <th>Score</th>
                    <th>Urgency</th>
                    <th>Segment</th>
                    <th>City</th>
                    <th>Units</th>
                  </tr>
                </thead>
                <tbody>
                  {ops.priority_queue.map((r) => (
                    <tr key={r.referral_id}>
                      <td>{r.referral_id}</td>
                      <td>{r.priority}</td>
                      <td>{r.score}</td>
                      <td>{r.urgency || '—'}</td>
                      <td>{r.agent_segment || '—'}</td>
                      <td>{r.patient_city || '—'}</td>
                      <td>{r.auth_units_remaining ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {ops.urgent_pending_preview.length > 0 && (
            <div className="dashboard-funnel">
              <h3>Urgent Pending (Preview)</h3>
              <table className="funnel-table">
                <thead>
                  <tr>
                    <th>Referral</th>
                    <th>Segment</th>
                    <th>City</th>
                    <th>Units</th>
                    <th>Received</th>
                  </tr>
                </thead>
                <tbody>
                  {ops.urgent_pending_preview.map((r) => (
                    <tr key={r.referral_id}>
                      <td>{r.referral_id}</td>
                      <td>{r.agent_segment || '—'}</td>
                      <td>{r.patient_city || '—'}</td>
                      <td>{r.auth_units_remaining ?? '—'}</td>
                      <td>{r.referral_received_date || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      <section className="dashboard-section">
        <h2 className="dashboard-title">Dataset Stats</h2>
        <div className="dashboard-stats">
          <div className="stat-card clickable" onClick={() => onNavigate('referrals')}>
            <div className="stat-value">{stats?.total_referrals || 0}</div>
            <div className="stat-label">Total Referrals</div>
            <div className="stat-hint">Click to view</div>
          </div>
          <div className="stat-card active clickable" onClick={() => onNavigate('referrals')}>
            <div className="stat-value">{stats?.active_referrals || 0}</div>
            <div className="stat-label">Active Referrals</div>
            <div className="stat-hint">Click to view</div>
          </div>
          <div className="stat-card clickable" onClick={() => onNavigate('caregivers')}>
            <div className="stat-value">{stats?.total_caregivers || 0}</div>
            <div className="stat-label">Total Caregivers</div>
            <div className="stat-hint">Click to view</div>
          </div>
          <div className="stat-card active clickable" onClick={() => onNavigate('caregivers')}>
            <div className="stat-value">{stats?.active_caregivers || 0}</div>
            <div className="stat-label">Active Caregivers</div>
            <div className="stat-hint">Click to view</div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Dashboard;
