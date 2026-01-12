import React, { useState } from 'react';
import './App.css';
import Dashboard from './components/Dashboard';
import ReferralTable from './components/ReferralTable';
import CaregiverTable from './components/CaregiverTable';
import AgentScheduler from './components/AgentScheduler';
import PdfIntake from './components/PdfIntake';
import ComplianceDocs from './components/ComplianceDocs';
import JourneyBoard from './components/JourneyBoard';

function App() {
  const [activeTab, setActiveTab] = useState<'referrals' | 'caregivers' | 'scheduler' | 'intake' | 'compliance' | 'journey'>('referrals');
  const [dataVersion, setDataVersion] = useState(0);
  const [selectedReferralId, setSelectedReferralId] = useState<string | null>(null);

  const handleNavigate = (tab: 'referrals' | 'caregivers' | 'scheduler' | 'intake' | 'compliance' | 'journey') => {
    setActiveTab(tab);
    // Scroll to the table section
    setTimeout(() => {
      document.querySelector('.tabs')?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const handleScheduleReferral = (referralId: string) => {
    setSelectedReferralId(referralId);
    setActiveTab('scheduler');
    setTimeout(() => {
      document.querySelector('.tabs')?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  const handleDataChanged = () => {
    setDataVersion((v) => v + 1);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>HealthOps Dashboard</h1>
        <p>Referral and Caregiver Management System</p>
      </header>

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
          Schedule Client
        </button>
        <button 
          className={activeTab === 'journey' ? 'tab-active' : ''} 
          onClick={() => setActiveTab('journey')}
        >
          Journey Board
        </button>
        <button 
          className={activeTab === 'intake' ? 'tab-active' : ''} 
          onClick={() => setActiveTab('intake')}
        >
          PDF Intake
        </button>
        <button 
          className={activeTab === 'compliance' ? 'tab-active' : ''} 
          onClick={() => setActiveTab('compliance')}
        >
          Compliance
        </button>
      </div>

      <div className="tab-content">
        {activeTab === 'referrals' && (
          <>
            <Dashboard onNavigate={handleNavigate} onDataChanged={handleDataChanged} dataVersion={dataVersion} />
            <ReferralTable dataVersion={dataVersion} onDataChanged={handleDataChanged} onScheduleReferral={handleScheduleReferral} />
          </>
        )}
        {activeTab === 'caregivers' && <CaregiverTable dataVersion={dataVersion} />}
        {activeTab === 'scheduler' && <AgentScheduler dataVersion={dataVersion} onDataChanged={handleDataChanged} initialReferralId={selectedReferralId} onReferralProcessed={() => setSelectedReferralId(null)} />}
        {activeTab === 'journey' && <JourneyBoard dataVersion={dataVersion} onDataChanged={handleDataChanged} />}
        {activeTab === 'intake' && <PdfIntake onDataChanged={handleDataChanged} onNavigate={handleNavigate} />}
        {activeTab === 'compliance' && <ComplianceDocs dataVersion={dataVersion} />}
      </div>
    </div>
  );
}

export default App;
