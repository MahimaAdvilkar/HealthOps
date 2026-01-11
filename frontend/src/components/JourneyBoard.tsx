import React, { useEffect, useMemo, useState } from 'react';
import { apiService, JourneyBoardResponse, JourneyBoardStage } from '../services/api';
import ReferralJourneyModal from './ReferralJourneyModal';
import '../styles/JourneyBoard.css';

interface JourneyBoardProps {
  dataVersion: number;
  onDataChanged: () => void;
}

const JourneyBoard: React.FC<JourneyBoardProps> = ({ dataVersion, onDataChanged }) => {
  const [board, setBoard] = useState<JourneyBoardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReferralId, setSelectedReferralId] = useState<string | null>(null);

  const stages: JourneyBoardStage[] = useMemo(() => board?.stages || [], [board]);

  const load = async () => {
    try {
      setLoading(true);
      const resp = await apiService.getJourneyBoard({ limitPerStage: 80 });
      setBoard(resp);
      setError(null);
    } catch (e) {
      console.error(e);
      setError('Failed to load journey board');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dataVersion]);

  if (loading) return <div className="loading">Loading journey board...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="journey-board">
      {selectedReferralId && (
        <ReferralJourneyModal
          referralId={selectedReferralId}
          onClose={() => setSelectedReferralId(null)}
          onDataChanged={onDataChanged}
        />
      )}

      <div className="journey-board-header">
        <div>
          <h2>Client Journey Board</h2>
          <div className="journey-board-subtitle">All clients grouped by operational stage (for demo).</div>
        </div>
        <button className="refresh-btn" onClick={load}>
          Refresh
        </button>
      </div>

      <div className="journey-columns">
        {stages.map((s) => (
          <div key={s.stage} className="journey-column">
            <div className="journey-column-header">
              <div className="journey-column-title">{s.label}</div>
              <div className="journey-column-count">{s.count}</div>
            </div>

            <div className="journey-cards">
              {s.referrals.length === 0 ? (
                <div className="journey-empty">No clients</div>
              ) : (
                s.referrals.map((r) => (
                  <div
                    key={r.referral_id}
                    className={`journey-card ${String(r.urgency || '').toLowerCase() === 'urgent' ? 'urgent' : ''}`}
                    onClick={() => setSelectedReferralId(r.referral_id)}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="journey-card-top">
                      <strong>{r.referral_id}</strong>
                      {r.urgency && <span className="journey-badge">{r.urgency}</span>}
                    </div>
                    <div className="journey-card-meta">
                      <div>📍 {r.patient_city || '—'}</div>
                      <div>🏷️ {r.payer || '—'}</div>
                      {r.auth_status && <div>🧾 Auth: {r.auth_status}</div>}
                      {r.schedule_status && <div>📅 {r.schedule_status}</div>}
                    </div>
                    <div className="journey-card-action">{r.agent_next_action || '—'}</div>
                  </div>
                ))
              )}
            </div>
          </div>
        ))}
      </div>

      {board?.generated_at && <div className="journey-board-footer">Updated: {new Date(board.generated_at).toLocaleString()}</div>}
    </div>
  );
};

export default JourneyBoard;
