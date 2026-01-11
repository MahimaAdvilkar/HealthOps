import React, { useCallback, useEffect, useState } from 'react';
import { apiService, Caregiver } from '../services/api';
import '../styles/CaregiverTable.css';

interface CaregiverTableProps {
  dataVersion: number;
}

const CaregiverTable: React.FC<CaregiverTableProps> = ({ dataVersion }) => {
  const [caregivers, setCaregivers] = useState<Caregiver[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    city: '',
    active: '',
    skills: '',
  });

  const loadCaregivers = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiService.getCaregivers({
        limit: 50,
        city: filters.city || undefined,
        active: filters.active || undefined,
        skills: filters.skills || undefined,
      });
      setCaregivers(data);
      setError(null);
    } catch (err) {
      setError('Failed to load caregivers');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadCaregivers();
  }, [loadCaregivers, dataVersion]);

  if (loading) return <div className="loading">Loading caregivers...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="caregiver-container">
      <div className="caregiver-header">
        <h2>Caregivers Dashboard</h2>
        <div className="filters">
          <input
            type="text"
            placeholder="Filter by city..."
            value={filters.city}
            onChange={(e) => setFilters({ ...filters, city: e.target.value })}
          />

          <select
            value={filters.active}
            onChange={(e) => setFilters({ ...filters, active: e.target.value })}
          >
            <option value="">All Status</option>
            <option value="Y">Active</option>
            <option value="N">Inactive</option>
          </select>

          <input
            type="text"
            placeholder="Filter by skills..."
            value={filters.skills}
            onChange={(e) => setFilters({ ...filters, skills: e.target.value })}
          />

          <button onClick={loadCaregivers} className="refresh-btn">Refresh</button>
        </div>
      </div>

      <div className="table-wrapper">
        <table className="caregiver-table">
          <thead>
            <tr>
              <th>Caregiver ID</th>
              <th>Gender</th>
              <th>Age</th>
              <th>Language</th>
              <th>Skills</th>
              <th>Employment</th>
              <th>Availability</th>
              <th>City</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {caregivers.map((caregiver) => (
              <tr key={caregiver.caregiver_id} className={caregiver.active === 'N' ? 'inactive' : ''}>
                <td><strong>{caregiver.caregiver_id}</strong></td>
                <td>{caregiver.gender || 'N/A'}</td>
                <td>{caregiver.age || 'N/A'}</td>
                <td>{caregiver.primary_language || 'N/A'}</td>
                <td className="skills-cell">{caregiver.skills || 'N/A'}</td>
                <td>{caregiver.employment_type || 'N/A'}</td>
                <td>{caregiver.availability || 'N/A'}</td>
                <td>{caregiver.city || 'N/A'}</td>
                <td>
                  <span className={`status-badge ${caregiver.active === 'Y' ? 'active' : 'inactive'}`}>
                    {caregiver.active === 'Y' ? 'Active' : 'Inactive'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="table-footer">
        <span>Total: {caregivers.length} caregivers</span>
      </div>
    </div>
  );
};

export default CaregiverTable;
