import React, { useCallback, useEffect, useState } from 'react';
import { apiService, Referral } from '../services/api';
import ReferralJourneyModal from './ReferralJourneyModal';
import '../styles/ReferralTable.css';

interface ReferralTableProps {
  dataVersion: number;
  onDataChanged: () => void;
  onScheduleReferral?: (referralId: string) => void;
}

const ReferralTable: React.FC<ReferralTableProps> = ({ dataVersion, onDataChanged, onScheduleReferral }) => {
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [journeyReferralId, setJourneyReferralId] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    urgency: '',
    agent_segment: '',
    schedule_status: '',
  });

  const loadReferrals = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiService.getReferrals({
        limit: 50,
        urgency: filters.urgency || undefined,
        agent_segment: filters.agent_segment || undefined,
        schedule_status: filters.schedule_status || undefined,
      });
      setReferrals(data);
      setError(null);
    } catch (err) {
      setError('Failed to load referrals');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadReferrals();
  }, [loadReferrals, dataVersion]);

  const getUrgencyClass = (urgency?: string) => {
    switch (urgency) {
      case 'Urgent': return 'urgency-urgent';
      case 'Routine': return 'urgency-routine';
      default: return '';
    }
  };

  const getSegmentClass = (segment?: string) => {
    switch (segment) {
      case 'RED': return 'segment-red';
      case 'ORANGE': return 'segment-orange';
      case 'GREEN': return 'segment-green';
      default: return '';
    }
  };

  if (loading) return <div className="loading">Loading referrals...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="referral-container">
      {journeyReferralId && (
        <ReferralJourneyModal
          referralId={journeyReferralId}
          onClose={() => setJourneyReferralId(null)}
          onDataChanged={onDataChanged}
        />
      )}
      <div className="referral-header">
        <h2>Referrals Dashboard</h2>
        <div className="filters">
          <select
            value={filters.urgency}
            onChange={(e) => setFilters({ ...filters, urgency: e.target.value })}
          >
            <option value="">All Urgency</option>
            <option value="Urgent">Urgent</option>
            <option value="Routine">Routine</option>
          </select>

          <select
            value={filters.agent_segment}
            onChange={(e) => setFilters({ ...filters, agent_segment: e.target.value })}
          >
            <option value="">All Segments</option>
            <option value="RED">RED</option>
            <option value="ORANGE">ORANGE</option>
            <option value="GREEN">GREEN</option>
          </select>

          <select
            value={filters.schedule_status}
            onChange={(e) => setFilters({ ...filters, schedule_status: e.target.value })}
          >
            <option value="">All Status</option>
            <option value="NOT_SCHEDULED">Not Scheduled</option>
            <option value="SCHEDULED">Scheduled</option>
            <option value="COMPLETED">Completed</option>
          </select>

          <button onClick={loadReferrals} className="refresh-btn">Refresh</button>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="referral-table">
          <thead>
            <tr>
              <th>Referral ID</th>
              <th>Service Type</th>
              <th>Urgency</th>
              <th>Segment</th>
              <th>Patient City</th>
              <th>Payer</th>
              <th>Schedule Status</th>
              <th>Units Remaining</th>
              <th>Next Action</th>
              <th>Contact Attempts</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {referrals.map((referral) => (
              <tr key={referral.referral_id}>
                <td><strong>{referral.referral_id}</strong></td>
                <td>{referral.service_type || 'N/A'}</td>
                <td>
                  <span className={`badge ${getUrgencyClass(referral.urgency)}`}>
                    {referral.urgency || 'N/A'}
                  </span>
                </td>
                <td>
                  <span className={`badge ${getSegmentClass(referral.agent_segment)}`}>
                    {referral.agent_segment || 'N/A'}
                  </span>
                </td>
                <td>{referral.patient_city || 'N/A'}</td>
                <td>{referral.payer || 'N/A'}</td>
                <td>{referral.schedule_status || 'N/A'}</td>
                <td>{referral.auth_units_remaining || 0}</td>
                <td className="action-cell">{referral.agent_next_action || 'N/A'}</td>
                <td>{referral.contact_attempts || 0}</td>
                <td className="actions-cell">
                  <button
                    className="action-btn analyze-btn"
                    onClick={() => onScheduleReferral?.(referral.referral_id)}
                    title="Analyze & Schedule"
                  >
                    Analyze
                  </button>
                  <button
                    className="action-btn view-btn"
                    onClick={() => setJourneyReferralId(referral.referral_id)}
                    title="View Journey"
                  >
                    Journey
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <span>Total: {referrals.length} referrals</span>
      </div>
    </div>
  );
};

export default ReferralTable;