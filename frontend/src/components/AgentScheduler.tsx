import React, { useState, useEffect } from 'react';
import { agentService, WorkflowResult, PendingReferral } from '../services/agentService';
import { AGENT_UI_CONFIG } from '../config/agentUiConfig';
import '../styles/AgentScheduler.css';

interface AgentSchedulerProps {
  dataVersion: number;
  onDataChanged: () => void;
}

const AgentScheduler: React.FC<AgentSchedulerProps> = ({ dataVersion, onDataChanged }) => {
  const [pendingReferrals, setPendingReferrals] = useState<PendingReferral[]>([]);
  const [selectedReferral, setSelectedReferral] = useState<PendingReferral | null>(null);
  const [workflowResult, setWorkflowResult] = useState<WorkflowResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [scheduleSuccess, setScheduleSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scheduleApplying, setScheduleApplying] = useState(false);
  const [scheduleMessage, setScheduleMessage] = useState<string | null>(null);

  useEffect(() => {
    loadPendingReferrals();
  }, [dataVersion]);

  const loadPendingReferrals = async () => {
    try {
      setLoading(true);
      const data = await agentService.getPendingReferrals();
      setPendingReferrals(data);
      setError(null);
    } catch (err) {
      setError('Failed to load pending referrals');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleProcessReferral = async (referral: PendingReferral) => {
    try {
      setProcessing(true);
      setSelectedReferral(referral);
      setWorkflowResult(null);
      setScheduleSuccess(false);
      
      const result = await agentService.processReferral(referral.referral_id);
      setWorkflowResult(result);
      setError(null);
    } catch (err) {
      setError('Failed to process referral');
      console.error(err);
    } finally {
      setProcessing(false);
    }
  };

  const handleScheduleNow = async () => {
    if (!workflowResult) return;
    if (!workflowResult.schedule_recommendation?.can_schedule) return;

    const caregiverId =
      workflowResult.schedule_recommendation.caregiver_id || workflowResult.matches?.[0]?.caregiver_id;
    if (!caregiverId) {
      setError('No caregiver available to schedule');
      return;
    }

    try {
      setScheduleApplying(true);
      setScheduleMessage(null);
      setError(null);

      const resp = await agentService.applySchedule({
        referral_id: workflowResult.referral_id,
        caregiver_id: caregiverId,
        schedule_status: 'SCHEDULED',
      });

      setScheduleSuccess(true);
      setScheduleMessage(`Scheduled ${resp.referral_id} with ${caregiverId} (${resp.mode})`);

      onDataChanged();
      await loadPendingReferrals();
    } catch (err) {
      setError('Failed to schedule referral');
      console.error(err);
    } finally {
      setScheduleApplying(false);
    }
  };

  const getStatusColor = (status: string) => {
    return AGENT_UI_CONFIG.statusColors[status as keyof typeof AGENT_UI_CONFIG.statusColors] 
      || AGENT_UI_CONFIG.statusColors.default;
  };

  const getActionColor = (action: string) => {
    if (!action) return AGENT_UI_CONFIG.actionColors.colors.default;
    
    const upperAction = action.toUpperCase();
    
    if (AGENT_UI_CONFIG.actionColors.scheduleKeywords.some(kw => upperAction.includes(kw))) {
      return AGENT_UI_CONFIG.actionColors.colors.schedule;
    }
    if (AGENT_UI_CONFIG.actionColors.holdKeywords.some(kw => upperAction.includes(kw))) {
      return AGENT_UI_CONFIG.actionColors.colors.hold;
    }
    if (AGENT_UI_CONFIG.actionColors.blockKeywords.some(kw => upperAction.includes(kw))) {
      return AGENT_UI_CONFIG.actionColors.colors.block;
    }
    
    return AGENT_UI_CONFIG.actionColors.colors.default;
  };

  if (loading) return <div className="loading">Loading pending referrals...</div>;

  return (
    <div className="agent-scheduler-container">
      <div className="scheduler-header">
        <h2>AI Agent Scheduler</h2>
        <p className="subtitle">3-Agent Workflow: Validation → Matching → Scheduling</p>
        <button onClick={loadPendingReferrals} className="refresh-btn">
          Refresh List
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}
      {scheduleMessage && <div className="success-message">{scheduleMessage}</div>}

      <div className="scheduler-layout">
        {/* Left Panel: Pending Referrals */}
        <div className="pending-panel">
          <h3>Waiting for Scheduling ({pendingReferrals.length})</h3>
          <div className="referral-list">
            {pendingReferrals.map((referral) => (
              <div
                key={referral.referral_id}
                className={`referral-card ${
                  selectedReferral?.referral_id === referral.referral_id ? 'selected' : ''
                }`}
                onClick={() => setSelectedReferral(referral)}
              >
                <div className="referral-header">
                  <strong>{referral.referral_id}</strong>
                  <span className={`urgency-badge ${referral.urgency?.toLowerCase()}`}>
                    {referral.urgency}
                  </span>
                </div>
                <div className="referral-details">
                  <div>{referral.service_type}</div>
                  <div>{referral.patient_city}</div>
                  <div>Units: {referral.auth_units_remaining}</div>
                </div>
                <button
                  className="process-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleProcessReferral(referral);
                  }}
                  disabled={processing}
                >
                  {processing && selectedReferral?.referral_id === referral.referral_id
                    ? 'Processing...'
                    : 'Analyze'}
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Right Panel: Agent Workflow Results */}
        <div className="workflow-panel">
          {!workflowResult && !selectedReferral && (
            <div className="empty-state">
              <h3>Select a referral to start</h3>
              <p>Click on any referral and run the AI agents to see the workflow</p>
            </div>
          )}

          {selectedReferral && !workflowResult && !processing && (
            <div className="selected-info">
              <h3>Selected: {selectedReferral.referral_id}</h3>
              <p>Click "Analyze" to process this referral</p>
            </div>
          )}

          {processing && (
            <div className="processing-state">
              <div className="spinner"></div>
              <h3>⚙️ AI Agents Working...</h3>
              <div className="agent-progress">
                <div className="agent-step">Agent 1: Validating referral</div>
                <div className="agent-step">Agent 2: Finding caregivers</div>
                <div className="agent-step">Agent 3: Creating schedule</div>
              </div>
            </div>
          )}

          {workflowResult && (
            <div className="workflow-results">
              <div className="result-header">
                <h3>Workflow Results: {workflowResult.referral_id}</h3>
                <span className="timestamp">{new Date(workflowResult.timestamp).toLocaleString()}</span>
              </div>

              {/* Agent 1: Validation */}
              <div className="agent-result">
                <div className="agent-title">
                  <span className="agent-icon">🔍</span>
                  <h4>Agent 1: Referral Validation</h4>
                </div>
                <div className="validation-status" style={{ backgroundColor: getStatusColor(workflowResult.validation.status) }}>
                  <strong>Status:</strong> {workflowResult.validation.status}
                </div>
                <div className="score-bar">
                  <div className="score-label">Validation Score</div>
                  <div className="score-progress">
                    <div
                      className="score-fill"
                      style={{
                        width: `${workflowResult.validation.validation_score}%`,
                        backgroundColor: workflowResult.validation.validation_score >= AGENT_UI_CONFIG.validation.passingScoreThreshold ? '#28a745' : '#dc3545'
                      }}
                    >
                      {workflowResult.validation.validation_score}%
                    </div>
                  </div>
                </div>

                {workflowResult.validation.issues.length > 0 && (
                  <div className="issues-section">
                    <strong>Issues:</strong>
                    <ul>
                      {workflowResult.validation.issues.map((issue, idx) => (
                        <li key={idx} className="issue-item">{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {workflowResult.validation.warnings.length > 0 && (
                  <div className="warnings-section">
                    <strong>⚠️ Warnings:</strong>
                    <ul>
                      {workflowResult.validation.warnings.map((warning, idx) => (
                        <li key={idx} className="warning-item">{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="recommendation-box" style={{ borderColor: getActionColor(workflowResult.validation_recommendation) }}>
                  <strong>💡 Agent Recommendation:</strong>
                  <p>{workflowResult.validation_recommendation}</p>
                </div>
              </div>

              {/* Agent 2: Matching */}
              <div className="agent-result">
                <div className="agent-title">
                  <span className="agent-icon">2</span>
                  <h4>Agent 2: Caregiver Matching</h4>
                </div>
                
                {workflowResult.matches.length > 0 ? (
                  <div className="matches-grid">
                    {workflowResult.matches.map((match, idx) => (
                      <div key={idx} className="match-card">
                        <div className="match-header">
                          <strong>{match.caregiver_id}</strong>
                          <span className="match-score">{match.match_score}%</span>
                        </div>
                        <div className="match-info">
                          <div>Location: {match.city}</div>
                          <div>Skills: {match.skills}</div>
                          <div>Availability: {match.availability}</div>
                          <div>🗣️ {match.language}</div>
                        </div>
                        <div className="match-reasons">
                          {match.match_reasons.map((reason, ridx) => (
                            <div key={ridx} className="reason-tag">✓ {reason}</div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="no-matches">No caregivers found in the area</div>
                )}

                <div className="recommendation-box" style={{ borderColor: getActionColor(workflowResult.matching_recommendation) }}>
                  <strong>💡 Agent Recommendation:</strong>
                  <p>{workflowResult.matching_recommendation}</p>
                </div>
              </div>

              {/* Agent 3: Scheduling */}
              <div className="agent-result">
                <div className="agent-title">
                  <span className="agent-icon">📅</span>
                  <h4>Agent 3: Scheduling Intelligence</h4>
                </div>

                <div className="schedule-details">
                  <div className="detail-row">
                    <span>Can Schedule:</span>
                    <strong className={workflowResult.schedule_recommendation.can_schedule ? 'text-success' : 'text-danger'}>
                      {workflowResult.schedule_recommendation.can_schedule ? '✓ YES' : '✗ NO'}
                    </strong>
                  </div>
                  <div className="detail-row">
                    <span>Action:</span>
                    <strong>{workflowResult.schedule_recommendation.schedule_action}</strong>
                  </div>
                  <div className="detail-row">
                    <span>Priority:</span>
                    <span className={`priority-badge ${workflowResult.schedule_recommendation.priority.toLowerCase()}`}>
                      {workflowResult.schedule_recommendation.priority}
                    </span>
                  </div>
                  {workflowResult.schedule_recommendation.suggested_units > 0 && (
                    <div className="detail-row">
                      <span>Suggested Units:</span>
                      <strong>{workflowResult.schedule_recommendation.suggested_units}</strong>
                    </div>
                  )}
                </div>

                {workflowResult.schedule_recommendation.rationale.length > 0 && (
                  <div className="rationale-section">
                    <strong>Rationale:</strong>
                    <ul>
                      {workflowResult.schedule_recommendation.rationale.map((item, idx) => (
                        <li key={idx}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {workflowResult.schedule_recommendation.next_steps.length > 0 && (
                  <div className="next-steps-section">
                    <strong>Next Steps:</strong>
                    <ol>
                      {workflowResult.schedule_recommendation.next_steps.map((step, idx) => (
                        <li key={idx}>{step}</li>
                      ))}
                    </ol>
                  </div>
                )}

                <div className="recommendation-box" style={{ borderColor: getActionColor(workflowResult.scheduling_recommendation) }}>
                  <strong>Agent Recommendation:</strong>
                  <p>{workflowResult.scheduling_recommendation}</p>
                </div>
              </div>

              {/* Final Action */}
              <div className="final-action-box">
                <h3>Final Workflow Status</h3>
                <div className="final-status">
                  <span>Status:</span>
                  <strong>{workflowResult.final_status}</strong>
                </div>
                <div className="final-action">
                  <span>Action:</span>
                  <strong>{workflowResult.final_action}</strong>
                </div>
                
                {workflowResult.schedule_recommendation.can_schedule && (
                  <button
                    className="schedule-now-btn"
                    onClick={handleScheduleNow}
                    disabled={scheduleApplying || scheduleSuccess}
                  >
                    {scheduleApplying ? 'Scheduling...' : scheduleSuccess ? 'Scheduled!' : 'Schedule Now'}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentScheduler;
