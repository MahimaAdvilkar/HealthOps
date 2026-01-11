# Agent Workflow Configuration Guide

## Overview
The AI Agent Workflow system is fully configurable with NO hardcoded values. All thresholds, scoring weights, limits, and UI settings are externalized to configuration files.

## Backend Configuration

### 1. Environment Variables (`.env`)
Location: `backend/.env`

```env
# Agent Workflow Configuration File Path
AGENT_CONFIG_PATH=config/agent_config.yaml

# API Keys
SWARMS_API_KEY=your_swarms_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=healthops_db
DB_USER=postgres
DB_PASSWORD=your_password
```

### 2. Agent Configuration (YAML)
Location: `backend/config/agent_config.yaml`

#### Validation Agent Settings
```yaml
validation_agent:
  scoring:
    insurance_inactive_penalty: 30      # Points deducted if insurance not active
    auth_not_approved_penalty: 40       # Points deducted if authorization not approved
    no_auth_units_penalty: 35          # Points deducted if no auth units remaining
    docs_incomplete_penalty: 10        # Points deducted for incomplete documentation
    no_home_assessment_penalty: 10     # Points deducted if home assessment not done
    low_responsiveness_penalty: 5      # Points deducted for low patient responsiveness
  
  thresholds:
    high_contact_attempts: 5           # Threshold for flagging high contact attempts
    passing_score: 70                  # Minimum score to pass validation
  
  status_mapping:
    ready: "READY"
    ready_with_warnings: "READY_WITH_WARNINGS"
    blocked: "BLOCKED"
    needs_docs: "NEEDS_DOCS"
```

#### Matching Agent Settings
```yaml
matching_agent:
  scoring:
    city_match_points: 40              # Points for exact city match
    exact_skill_match_points: 40       # Points for exact skill match
    general_skill_match_points: 20     # Points for general skill match
    flexible_availability_points: 20   # Points for flexible/full-time availability
    partial_availability_points: 10    # Points for partial availability
  
  thresholds:
    minimum_match_score: 30            # Minimum score to include in matches
    max_matches_returned: 5            # Maximum number of matches to return
  
  general_skills:                      # List of general skills that count as matches
    - "ECM"
    - "HOME"
    - "CARE"
```

#### Scheduling Agent Settings
```yaml
scheduling_agent:
  limits:
    max_units_per_week: 20            # Maximum units to schedule per week
    max_pending_referrals: 50         # Maximum pending referrals to return
  
  priorities:
    urgent_keywords:                   # Keywords that trigger high priority
      - "Urgent"
      - "STAT"
      - "Emergency"
    high_priority: "HIGH"
    normal_priority: "NORMAL"
  
  actions:
    schedule_now: "SCHEDULE_NOW"
    hold: "HOLD"
    block: "BLOCK"
  
  unit_calculation:
    min_suggested_units: 1
    default_buffer: 0
```

#### Workflow Settings
```yaml
workflow:
  enable_parallel_processing: false
  max_retry_attempts: 3
  timeout_seconds: 30
```

## Frontend Configuration

### 3. UI Configuration (TypeScript)
Location: `frontend/src/config/agentUiConfig.ts`

```typescript
export const AGENT_UI_CONFIG = {
  validation: {
    passingScoreThreshold: 70,         // Minimum score for green color (must match backend)
    colors: {
      pass: '#28a745',                 // Green for passing scores
      fail: '#dc3545'                  // Red for failing scores
    }
  },
  
  statusColors: {
    READY: '#28a745',
    READY_WITH_WARNINGS: '#ffc107',
    BLOCKED: '#dc3545',
    NEEDS_DOCS: '#6c757d',
    default: '#6c757d'
  },
  
  actionColors: {
    scheduleKeywords: ['SCHEDULE NOW', 'SCHEDULE_NOW', 'PROCEED'],
    holdKeywords: ['HOLD', 'WAIT', 'CAUTION'],
    blockKeywords: ['BLOCK', 'CANNOT', 'FAILED'],
    colors: {
      schedule: '#28a745',
      hold: '#ffc107',
      block: '#dc3545',
      default: '#007bff'
    }
  },
  
  priorityColors: {
    HIGH: '#dc3545',
    NORMAL: '#28a745',
    LOW: '#6c757d'
  }
};
```

## How to Customize

### Adjusting Scoring Weights
To change how agents score referrals and matches, edit `backend/config/agent_config.yaml`:

**Example:** Make city matching worth more:
```yaml
matching_agent:
  scoring:
    city_match_points: 50    # Changed from 40
    exact_skill_match_points: 30    # Changed from 40
```

### Changing Validation Thresholds
To make validation more or less strict:

```yaml
validation_agent:
  thresholds:
    passing_score: 80          # Changed from 70 - now stricter
  scoring:
    insurance_inactive_penalty: 50    # Increased penalty
```

### Adjusting UI Colors
To change the UI appearance, edit `frontend/src/config/agentUiConfig.ts`:

```typescript
validation: {
  passingScoreThreshold: 80,   // Must match backend passing_score
  colors: {
    pass: '#00a65a',          // Different shade of green
    fail: '#ff4444'           // Different shade of red
  }
}
```

### Modifying Match Limits
To return more or fewer caregiver matches:

```yaml
matching_agent:
  thresholds:
    max_matches_returned: 10   # Changed from 5
```

### Updating Urgent Keywords
To add more keywords that trigger high priority:

```yaml
scheduling_agent:
  priorities:
    urgent_keywords:
      - "Urgent"
      - "STAT"
      - "Emergency"
      - "Critical"          # New
      - "Immediate"         # New
```

## Configuration Validation

The system uses default values if configuration is missing:
- If YAML file is not found, hardcoded defaults are used
- If a specific key is missing, the default value in the code is used
- All defaults are documented in the code comments

## Best Practices

1. **Keep Frontend and Backend in Sync**: The `passingScoreThreshold` in frontend should match `passing_score` in backend
2. **Test After Changes**: Restart backend after changing YAML config
3. **Use Version Control**: Track changes to config files
4. **Document Custom Changes**: Add comments in YAML for non-standard values
5. **Validate Scoring**: Ensure scoring weights add up logically (e.g., city + skills + availability = 100)

## Configuration Loading Order

1. Backend reads `.env` file
2. Backend loads `AGENT_CONFIG_PATH` from `.env`
3. Backend reads YAML configuration file
4. Each agent initializes with config values
5. Frontend loads `agentUiConfig.ts` at compile time

## Troubleshooting

**Agent not using new config values:**
- Restart the FastAPI server: `uvicorn app:app --reload`
- Check YAML syntax is valid
- Verify file path in `.env` is correct

**UI colors not matching backend logic:**
- Check `passingScoreThreshold` matches backend `passing_score`
- Verify status strings match between frontend and backend
- Clear browser cache and rebuild frontend

**Getting default values instead of config:**
- Check YAML file exists at path specified in `.env`
- Verify YAML syntax (use online YAML validator)
- Check file permissions

## Example Scenarios

### Scenario 1: Prioritize Skills Over Location
```yaml
matching_agent:
  scoring:
    city_match_points: 30
    exact_skill_match_points: 50
```

### Scenario 2: Stricter Validation
```yaml
validation_agent:
  scoring:
    insurance_inactive_penalty: 50
    auth_not_approved_penalty: 50
  thresholds:
    passing_score: 85
```

### Scenario 3: More Pending Referrals
```yaml
scheduling_agent:
  limits:
    max_pending_referrals: 100
```

## Files Modified

All hardcoding removed from:
- ✅ `backend/src/services/agent_workflow.py` - All agents use config
- ✅ `backend/app.py` - Uses config for limits
- ✅ `frontend/src/components/AgentScheduler.tsx` - Uses UI config
- ✅ `backend/config/agent_config.yaml` - Central configuration
- ✅ `frontend/src/config/agentUiConfig.ts` - UI configuration
