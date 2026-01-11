import React, { useEffect, useMemo, useState } from 'react';
import { apiService, ReferralJourneyResponse } from '../services/api';
import '../styles/ReferralJourneyModal.css';

interface Props {
  referralId: string;
  onClose: () => void;
  onDataChanged: () => void;
}

const stageOrder = [
  'INTAKE_RECEIVED',
  'DOCS_COMPLETED',
  'HOME_ASSESSMENT_SCHEDULED',
  'HOME_ASSESSMENT_COMPLETED',
  'SCHEDULED',
  'SERVICE_STARTED',
  'READY_TO_BILL',
  'SERVICE_COMPLETED',
];

function nextSuggestedStages(current: string): string[] {
  const idx = stageOrder.indexOf((current || '').toUpperCase());
  if (idx === -1) return ['DOCS_COMPLETED'];
  const candidates = stageOrder.slice(idx + 1);
  // Don't allow setting SCHEDULED here; that is done by the Scheduler tab
  return candidates.filter((s) => s !== 'SCHEDULED').slice(0, 3);
}

const ReferralJourneyModal: React.FC<Props> = ({ referralId, onClose, onDataChanged }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [journey, setJourney] = useState<ReferralJourneyResponse | null>(null);
  const [note, setNote] = useState('');
  const [advancing, setAdvancing] = useState<string | null>(null);

  const suggested = useMemo(() => nextSuggestedStages(journey?.current_stage || ''), [journey?.current_stage]);

  const load = async () => {
    try {
      setLoading(true);
      const resp = await apiService.getReferralJourney(referralId);
      setJourney(resp);
      setError(null);
    } catch (e) {
      console.error(e);
      setError('Failed to load journey');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [referralId]);

  const handleAdvance = async (stage: string) => {
    try {
      setAdvancing(stage);
      await apiService.advanceReferralJourney(referralId, stage, note || undefined);
      setNote('');
      onDataChanged();
      await load();
    } catch (e) {
      console.error(e);
      setError('Failed to advance journey');
    } finally {
      setAdvancing(null);
    }
  };

  return (
    <div className="journey-overlay" onClick={onClose}>
      <div className="journey-modal" onClick={(e) => e.stopPropagation()}>
        <div className="journey-header">
          <h3>Referral Journey: {referralId}</h3>
          <button className="journey-close" onClick={onClose}>
            ✕
          </button>
        </div>

        {loading && <div className="loading">Loading journey…</div>}
        {error && <div className="error">{error}</div>}

        {journey && (
          <>
            <div className="journey-current">
              <strong>Current stage:</strong> {journey.current_stage}
            </div>

            <div className="journey-actions">
              <div className="journey-note">
                <label>Note (optional)</label>
                <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g., patient called back" />
              </div>

              <div className="journey-buttons">
                {suggested.map((s) => (
                  <button key={s} disabled={!!advancing} onClick={() => handleAdvance(s)}>
                    {advancing === s ? 'Updating…' : `Mark ${s.replaceAll('_', ' ')}`}
                  </button>
                ))}
              </div>
              <div className="journey-hint">Scheduling is done from the AI Scheduler tab.</div>
            </div>

            <div className="journey-timeline">
              <h4>Timeline</h4>
              <ul>
                {journey.timeline
                  .slice()
                  .reverse()
                  .map((ev, idx) => (
                    <li key={`${ev.stage}-${idx}`}>
                      <div className="journey-stage">{ev.stage}</div>
                      <div className="journey-meta">
                        {ev.at ? new Date(ev.at).toLocaleString() : '—'} • {ev.source || '—'}
                      </div>
                      {ev.note && <div className="journey-note-text">{ev.note}</div>}
                    </li>
                  ))}
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default ReferralJourneyModal;
