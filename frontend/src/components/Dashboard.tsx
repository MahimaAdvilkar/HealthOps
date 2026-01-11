import React, { useEffect, useState } from 'react';
import { apiService, Stats } from '../services/api';
import '../styles/Dashboard.css';

interface DashboardProps {
  onNavigate: (tab: 'referrals' | 'caregivers') => void;
}

const Dashboard: React.FC<DashboardProps> = ({ onNavigate }) => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const data = await apiService.getStats();
      setStats(data);
    } catch (err) {
      console.error('Failed to load stats:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading statistics...</div>;

  return (
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
  );
};

export default Dashboard;
