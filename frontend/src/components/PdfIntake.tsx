import React, { useMemo, useState } from 'react';
import { apiService, PdfIntakeResponse } from '../services/api';
import '../styles/PdfIntake.css';

interface PdfIntakeProps {
  onDataChanged: () => void;
  onNavigate: (tab: 'referrals' | 'caregivers' | 'scheduler' | 'intake' | 'compliance' | 'journey' | 'viz') => void;
}

const PdfIntake: React.FC<PdfIntakeProps> = ({ onDataChanged, onNavigate }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PdfIntakeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = useMemo(() => files.length > 0 && !loading, [files.length, loading]);

  const handleFilesChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    setFiles(selected);
    setResult(null);
    setError(null);
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      setError(null);
      setResult(null);

      const resp = await apiService.intakeFromPdf(files);
      setResult(resp);

      if (resp.created.length > 0) {
        onDataChanged();
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to intake PDFs');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pdf-intake">
      <h2 className="pdf-intake-title">PDF Intake (LandingAI)</h2>
      <p className="pdf-intake-subtitle">
        Upload one or more PDFs, parse with LandingAI, and insert new referrals into the same operational pipeline.
      </p>

      <div className="pdf-intake-card">
        <input type="file" accept="application/pdf" multiple onChange={handleFilesChange} />

        <button className="pdf-intake-btn" disabled={!canSubmit} onClick={handleSubmit}>
          {loading ? 'Parsing…' : 'Parse PDFs & Create Referrals'}
        </button>

        {files.length > 0 && (
          <div className="pdf-intake-files">
            <div className="pdf-intake-files-title">Selected files</div>
            <ul>
              {files.map((f) => (
                <li key={f.name}>{f.name}</li>
              ))}
            </ul>
          </div>
        )}

        {error && <div className="pdf-intake-error">{error}</div>}

        {result && (
          <div className="pdf-intake-result">
            <div className="pdf-intake-result-title">
              Created: {result.created.length} • Compliance: {result.compliance_saved?.length || 0} • Ignored:{' '}
              {result.ignored?.length || 0} • Errors: {result.errors.length} • Mode: {result.mode}
            </div>

            {result.created.length > 0 && (
              <div className="pdf-intake-created">
                <div className="pdf-intake-created-title">New referrals</div>
                <ul>
                  {result.created.map((c) => (
                    <li key={c.referral.referral_id}>
                      {c.referral.referral_id} — {c.source_filename}
                      {c.classification?.confidence !== undefined && (
                        <span style={{ color: '#666' }}>
                          {' '}({c.classification.type}, {Math.round(c.classification.confidence * 100)}%)
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
                <div className="pdf-intake-actions">
                  <button className="pdf-intake-link" onClick={() => onNavigate('referrals')}>
                    View Referrals
                  </button>
                  <button className="pdf-intake-link" onClick={() => onNavigate('scheduler')}>
                    Go to Scheduler
                  </button>
                </div>
              </div>
            )}

            {(result.compliance_saved?.length || 0) > 0 && (
              <div className="pdf-intake-created">
                <div className="pdf-intake-created-title">Compliance guardrails saved</div>
                <ul>
                  {result.compliance_saved!.map((c) => (
                    <li key={c.compliance_id}>
                      {c.source_filename} — {c.compliance_id}{' '}
                      <span style={{ color: '#666' }}>
                        (compliance, {Math.round(c.classification.confidence * 100)}%)
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {(result.ignored?.length || 0) > 0 && (
              <div className="pdf-intake-created">
                <div className="pdf-intake-created-title">Ignored (not a referral)</div>
                <ul>
                  {result.ignored!.map((i) => (
                    <li key={i.source_filename}>
                      {i.source_filename}{' '}
                      <span style={{ color: '#666' }}>
                        ({i.classification.type}, {Math.round(i.classification.confidence * 100)}%)
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {result.errors.length > 0 && (
              <div className="pdf-intake-errors">
                <div className="pdf-intake-created-title">Errors</div>
                <ul>
                  {result.errors.map((e) => (
                    <li key={e.filename}>
                      {e.filename}: {e.error}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default PdfIntake;
