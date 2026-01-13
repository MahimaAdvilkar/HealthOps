import React, { useEffect, useMemo, useState, useId } from 'react';
import { apiService, Caregiver, JourneyBoardStage, Referral } from '../services/api';
import '../styles/DataVizAgent.css';

interface DataVizAgentProps {
  dataVersion: number;
}

interface BarDatum {
  label: string;
  value: number;
}

const toDateKey = (date: Date) => date.toISOString().slice(0, 10);

const formatShortDate = (date: Date) => {
  const month = date.getMonth() + 1;
  const day = date.getDate();
  return `${month}/${day}`;
};

const countBy = <T,>(items: T[], getKey: (item: T) => string) => {
  const map = new Map<string, number>();
  items.forEach((item) => {
    const key = getKey(item);
    map.set(key, (map.get(key) || 0) + 1);
  });
  return map;
};

const toBarData = (map: Map<string, number>, limit = 6): BarDatum[] => {
  return Array.from(map.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit);
};

const MiniLineChart: React.FC<{
  data: number[];
  labels: string[];
  stroke?: string;
}> = ({ data, labels, stroke = '#2563eb' }) => {
  const gradientId = useId();
  const width = 320;
  const height = 140;
  const padding = 18;

  if (data.length === 0) {
    return <div className="viz-empty">No recent referral dates found.</div>;
  }

  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = Math.max(max - min, 1);

  const points = data.map((value, index) => {
    const x = padding + (index / Math.max(data.length - 1, 1)) * (width - padding * 2);
    const y = height - padding - ((value - min) / range) * (height - padding * 2);
    return { x, y };
  });

  const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
  const areaPath = `${path} L ${points[points.length - 1].x},${height - padding} L ${points[0].x},${height - padding} Z`;

  const labelIndexes = [0, Math.floor((labels.length - 1) / 2), labels.length - 1].filter(
    (value, index, arr) => arr.indexOf(value) === index
  );

  return (
    <div className="viz-line-wrap">
      <svg className="viz-line" viewBox={`0 0 ${width} ${height}`} role="img">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity="0.2" />
            <stop offset="100%" stopColor={stroke} stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <path d={areaPath} fill={`url(#${gradientId})`} />
        <path d={path} fill="none" stroke={stroke} strokeWidth="2.5" strokeLinecap="round" />
      </svg>
      <div className="viz-xlabels">
        {labelIndexes.map((idx) => (
          <span key={labels[idx]}>{labels[idx]}</span>
        ))}
      </div>
    </div>
  );
};

const MiniBarChart: React.FC<{ data: BarDatum[]; color?: string }> = ({ data, color = '#0ea5e9' }) => {
  if (data.length === 0) {
    return <div className="viz-empty">No data available.</div>;
  }

  const max = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="viz-bars">
      {data.map((item) => (
        <div key={item.label} className="viz-bar-row">
          <div className="viz-bar-label">{item.label}</div>
          <div className="viz-bar-track">
            <div className="viz-bar-fill" style={{ width: `${(item.value / max) * 100}%`, background: color }} />
          </div>
          <div className="viz-bar-value">{item.value}</div>
        </div>
      ))}
    </div>
  );
};

const DataVizAgent: React.FC<DataVizAgentProps> = ({ dataVersion }) => {
  const [referrals, setReferrals] = useState<Referral[]>([]);
  const [caregivers, setCaregivers] = useState<Caregiver[]>([]);
  const [journeyStages, setJourneyStages] = useState<JourneyBoardStage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  const loadData = async () => {
    setLoading(true);
    setError(null);

    const [refResult, careResult, journeyResult] = await Promise.allSettled([
      apiService.getReferrals({ limit: 1000 }),
      apiService.getCaregivers({ limit: 500 }),
      apiService.getJourneyBoard({ limitPerStage: 100 }),
    ]);

    const errors: string[] = [];

    if (refResult.status === 'fulfilled') {
      setReferrals(refResult.value);
    } else {
      errors.push('Referrals');
      setReferrals([]);
    }

    if (careResult.status === 'fulfilled') {
      setCaregivers(careResult.value);
    } else {
      errors.push('Caregivers');
      setCaregivers([]);
    }

    if (journeyResult.status === 'fulfilled') {
      setJourneyStages(journeyResult.value.stages);
    } else {
      errors.push('Journey board');
      setJourneyStages([]);
    }

    if (errors.length > 0) {
      setError(`Some data failed to load (${errors.join(', ')}).`);
    }

    setLastUpdated(new Date().toLocaleString());
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, [dataVersion]);

  const dailyTrend = useMemo(() => {
    const today = new Date();
    const dates = Array.from({ length: 14 }, (_, idx) => {
      const date = new Date(today);
      date.setDate(today.getDate() - (13 - idx));
      return date;
    });

    const counts = new Map<string, number>();
    referrals.forEach((ref) => {
      if (!ref.referral_received_date) return;
      const date = new Date(ref.referral_received_date);
      if (Number.isNaN(date.getTime())) return;
      const key = toDateKey(date);
      counts.set(key, (counts.get(key) || 0) + 1);
    });

    const labels = dates.map(formatShortDate);
    const values = dates.map((date) => counts.get(toDateKey(date)) || 0);

    const last7 = values.slice(-7).reduce((sum, val) => sum + val, 0);
    const prev7 = values.slice(0, 7).reduce((sum, val) => sum + val, 0);
    const delta = prev7 ? (last7 - prev7) / prev7 : 0;

    return {
      labels,
      values,
      last7,
      prev7,
      delta,
    };
  }, [referrals]);

  const forecast = useMemo(() => {
    const avgDaily = dailyTrend.last7 / 7;
    const next7 = Math.round(avgDaily * 7);
    const pendingLast7 = referrals
      .filter((ref) => ref.schedule_status && ref.schedule_status.toLowerCase().includes('pending'))
      .filter((ref) => {
        if (!ref.referral_received_date) return false;
        const date = new Date(ref.referral_received_date);
        if (Number.isNaN(date.getTime())) return false;
        const daysAgo = (Date.now() - date.getTime()) / (1000 * 60 * 60 * 24);
        return daysAgo <= 7;
      }).length;
    const pendingRatio = dailyTrend.last7 ? pendingLast7 / dailyTrend.last7 : 0;

    return {
      next7,
      pendingNext7: Math.round(next7 * pendingRatio),
      avgDaily: avgDaily.toFixed(1),
    };
  }, [dailyTrend.last7, referrals]);

  const scheduleData = useMemo(() => {
    return toBarData(countBy(referrals, (ref) => ref.schedule_status || 'Unknown'));
  }, [referrals]);

  const urgencyData = useMemo(() => {
    return toBarData(countBy(referrals, (ref) => ref.urgency || 'Unknown'));
  }, [referrals]);

  const caregiverStatus = useMemo(() => {
    const active = caregivers.filter((c) => (c.active || '').toUpperCase() === 'Y').length;
    const inactive = caregivers.length - active;
    return { active, inactive, total: caregivers.length };
  }, [caregivers]);

  const journeyData = useMemo(() => {
    if (!journeyStages.length) return [];
    return journeyStages
      .map((stage) => ({ label: stage.label, value: stage.count }))
      .sort((a, b) => b.value - a.value);
  }, [journeyStages]);

  const trendLabel = dailyTrend.prev7
    ? `${dailyTrend.delta >= 0 ? 'Up' : 'Down'} ${Math.abs(dailyTrend.delta * 100).toFixed(1)}% vs prior 7d`
    : 'Not enough history for trend';

  return (
    <div className="data-viz">
      <div className="data-viz-header">
        <div>
          <h2>Data Visualization Agent</h2>
          <p>Graphs and short-term predictions across your HealthOps activity.</p>
        </div>
        <div className="data-viz-meta">
          <div className="data-viz-meta-label">Last refresh</div>
          <div className="data-viz-meta-value">{lastUpdated || '—'}</div>
          <button className="data-viz-refresh" onClick={loadData} disabled={loading}>
            {loading ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && <div className="data-viz-error">{error}</div>}
      {loading ? (
        <div className="loading">Loading visualizations…</div>
      ) : (
        <>
          <div className="data-viz-grid">
            <div className="viz-card wide">
              <div className="viz-card-header">
                <h3>Referrals Received (Last 14 Days)</h3>
                <span className="viz-subtle">{trendLabel}</span>
              </div>
              <MiniLineChart data={dailyTrend.values} labels={dailyTrend.labels} />
              <div className="viz-kpis">
                <div>
                  <div className="viz-kpi-value">{dailyTrend.last7}</div>
                  <div className="viz-kpi-label">Total last 7d</div>
                </div>
                <div>
                  <div className="viz-kpi-value">{forecast.avgDaily}</div>
                  <div className="viz-kpi-label">Avg per day</div>
                </div>
                <div>
                  <div className="viz-kpi-value">{referrals.length}</div>
                  <div className="viz-kpi-label">Total referrals</div>
                </div>
              </div>
            </div>

            <div className="viz-card">
              <div className="viz-card-header">
                <h3>Predictions</h3>
                <span className="viz-subtle">Based on last 7 days</span>
              </div>
              <div className="viz-predictions">
                <div>
                  <div className="viz-kpi-value">{forecast.next7}</div>
                  <div className="viz-kpi-label">Forecast referrals (next 7d)</div>
                </div>
                <div>
                  <div className="viz-kpi-value">{forecast.pendingNext7}</div>
                  <div className="viz-kpi-label">Forecast pending scheduling</div>
                </div>
              </div>
              <div className="viz-footnote">Simple projection using recent arrival rate and pending ratio.</div>
            </div>

            <div className="viz-card">
              <div className="viz-card-header">
                <h3>Schedule Status</h3>
              </div>
              <MiniBarChart data={scheduleData} color="#6366f1" />
            </div>

            <div className="viz-card">
              <div className="viz-card-header">
                <h3>Urgency Mix</h3>
              </div>
              <MiniBarChart data={urgencyData} color="#ef4444" />
            </div>

            <div className="viz-card">
              <div className="viz-card-header">
                <h3>Caregiver Status</h3>
              </div>
              <div className="viz-donut-wrap">
                <div
                  className="viz-donut"
                  style={{
                    background: `conic-gradient(#10b981 ${(caregiverStatus.active / Math.max(caregiverStatus.total, 1)) * 360}deg, #e5e7eb 0deg)`,
                  }}
                />
                <div className="viz-donut-legend">
                  <div>
                    <span className="viz-dot active" /> Active
                    <span className="viz-donut-value">{caregiverStatus.active}</span>
                  </div>
                  <div>
                    <span className="viz-dot inactive" /> Inactive
                    <span className="viz-donut-value">{caregiverStatus.inactive}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="viz-card">
              <div className="viz-card-header">
                <h3>Journey Stages</h3>
              </div>
              <MiniBarChart data={journeyData} color="#14b8a6" />
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default DataVizAgent;
