import React, { useEffect, useState } from 'react';
import { apiService, ComplianceDoc } from '../services/api';
import '../styles/ComplianceDocs.css';

interface ComplianceDocsProps {
  dataVersion: number;
}

const ComplianceDocs: React.FC<ComplianceDocsProps> = ({ dataVersion }) => {
  const [docs, setDocs] = useState<ComplianceDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const resp = await apiService.getComplianceDocs({ limit: 50 });
        setDocs(resp.docs || []);
        setError(null);
      } catch (e) {
        console.error(e);
        setError('Failed to load compliance guardrails');
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [dataVersion]);

  if (loading) return <div className="loading">Loading compliance guardrails...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="compliance-container">
      <div className="compliance-header">
        <h2>Compliance Guardrails</h2>
        <p className="compliance-subtitle">PDFs classified as compliance are stored here and act as reference guardrails.</p>
      </div>

      {docs.length === 0 ? (
        <div className="compliance-empty">No compliance documents ingested yet.</div>
      ) : (
        <div className="compliance-list">
          {docs.map((d) => (
            <div key={d.compliance_id} className="compliance-card">
              <div className="compliance-card-title">
                <strong>{d.source_filename}</strong>
                <span className="compliance-id">{d.compliance_id}</span>
              </div>
              <div className="compliance-meta">{new Date(d.created_at).toLocaleString()}</div>
              {d.excerpt && <div className="compliance-excerpt">{d.excerpt}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default ComplianceDocs;
