import React, { useState } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import ReferralTable from './components/ReferralTable';
import CaregiverTable from './components/CaregiverTable';
import AgentScheduler from './components/AgentScheduler';

function App() {
  const [activeTab, setActiveTab] = useState<'referrals' | 'caregivers' | 'scheduler'>('referrals');

  const handleNavigate = (tab: 'referrals' | 'caregivers') => {
    setActiveTab(tab);
    // Scroll to the table section
    setTimeout(() => {
      document.querySelector('.tabs')?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>HealthOps Dashboard</h1>
        <p>Referral and Caregiver Management System</p>
      </header>

      <Dashboard onNavigate={handleNavigate} />

      <div className="tabs">
        <button 
          className={activeTab === 'referrals' ? 'tab-active' : ''} 
          onClick={() => setActiveTab('referrals')}
        >
          Referrals
        </button>
        <button 
          className={activeTab === 'caregivers' ? 'tab-active' : ''} 
          onClick={() => setActiveTab('caregivers')}
        >
          Caregivers
        </button>
        <button 
          className={activeTab === 'scheduler' ? 'tab-active' : ''} 
          onClick={() => setActiveTab('scheduler')}
        >
          AI Scheduler
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'referrals' && <ReferralTable />}
        {activeTab === 'caregivers' && <CaregiverTable />}
        {activeTab === 'scheduler' && <AgentScheduler />}
      </div>
    </div>
  );
}

export default App;
