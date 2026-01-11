// Frontend configuration for Agent Scheduler UI
export const AGENT_UI_CONFIG = {
  validation: {
    passingScoreThreshold: 70, // Minimum score for green color
    colors: {
      pass: '#28a745',
      fail: '#dc3545'
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
