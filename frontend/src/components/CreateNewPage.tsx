import React, { useState } from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';

const CreateNewPage: React.FC = () => {
  const [agentName, setAgentName] = useState('Untitled Agent');
  const [selectedVoice, setSelectedVoice] = useState('Vincent');
  const [selectedSpeed, setSelectedSpeed] = useState('1.0x');
  const [selectedModel, setSelectedModel] = useState('Play 2.0 (Most Stable)');
  const [selectedPrivacy, setSelectedPrivacy] = useState('Public');
  const [currentStep, setCurrentStep] = useState('identity');

  const voices = ['Vincent', 'Alice', 'Bob', 'Emma'];
  const speeds = ['0.5x', '0.75x', '1.0x', '1.25x', '1.5x', '2.0x'];
  const models = ['Play 2.0 (Most Stable)', 'Play 3.0 (Beta)', 'GPT-4'];
  const privacyOptions = ['Public', 'Private', 'Unlisted'];


  const steps = [
    { id: 'identity', label: 'Identity', completed: true },
    { id: 'behavior', label: 'Behavior', completed: false },
    { id: 'knowledge', label: 'Knowledge', completed: false },
    { id: 'actions', label: 'Actions', completed: false },
    { id: 'deploy-phone', label: 'Deploy • Phone', completed: false },
    { id: 'deploy-web', label: 'Deploy • Web', completed: false },
  ];

  return (
    <div className="flex h-full bg-black text-white">
      
      {/* Left Navigation Panel */}
      <div className="w-80 bg-black flex flex-col">
        <div className="flex-1 flex items-center justify-center">
          <div className="space-y-1">
            {steps.map((step, index) => (
              <div 
                key={step.id}
                className={`flex items-center space-x-3 px-6 py-3 rounded-full cursor-pointer transition-all ${
                  step.id === currentStep 
                    ? 'bg-white text-black' 
                    : step.completed 
                      ? 'text-white hover:bg-white/10'
                      : 'text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50'
                }`}
                onClick={() => setCurrentStep(step.id)}
              >
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                  step.id === currentStep 
                    ? 'bg-black text-white' 
                    : step.completed 
                      ? 'bg-white text-black'
                      : 'bg-neutral-700 text-neutral-400'
                }`}>
                  {step.completed ? (
                    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  ) : (
                    <span className="text-xs font-medium">{index + 1}</span>
                  )}
                </div>
                <span className="text-sm font-medium">{step.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Center Content Area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-center p-6">
          <h1 className="text-xl font-medium text-neutral-400">YOUR AGENT</h1>
          <button className="absolute top-6 right-6 bg-white hover:bg-gray-200 text-black font-medium px-6 py-2 rounded-full transition-colors">
            Save Agent
          </button>
        </div>

        {/* Main content container */}
        <div className="flex-1 overflow-y-auto p-6 pr-3 relative">
          <div className="max-w-lg ml-auto mr-6 relative">
            {/* Form Container */}
            <div className="bg-neutral-900/80 rounded-2xl p-8 space-y-6 border border-neutral-700/50">
          
          {/* Name Section */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <div className="w-6 h-6 rounded-full bg-neutral-600 flex items-center justify-center">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
              </div>
              <span className="text-sm font-medium text-neutral-400">NAME</span>
            </div>
            <input
              type="text"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              className="w-full bg-black/50 border border-neutral-700 rounded-2xl px-5 py-2.5 text-white placeholder-neutral-400 focus:outline-none focus:border-white/30 transition-colors"
              placeholder="Enter agent name"
            />
          </div>

          {/* Voice Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
                <span className="text-sm font-medium text-neutral-400">Voice</span>
              </div>
              <div className="flex items-center space-x-2">
                <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5.636 5.636a9 9 0 1012.728 0M12 3v9" />
                </svg>
                <span className="text-sm font-medium text-neutral-400">SPEED</span>
              </div>
            </div>
            
            <div className="flex space-x-4">
              <div className="flex-1 relative">
                <select
                  value={selectedVoice}
                  onChange={(e) => setSelectedVoice(e.target.value)}
                  className="w-full bg-black/50 border border-neutral-700 rounded-2xl px-5 py-2.5 text-white appearance-none focus:outline-none focus:border-white/30 cursor-pointer transition-colors"
                >
                  {voices.map(voice => (
                    <option key={voice} value={voice}>{voice}</option>
                  ))}
                </select>
                <ChevronDownIcon className="absolute right-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white pointer-events-none" />
              </div>
              
              <div className="w-28 relative">
                <select
                  value={selectedSpeed}
                  onChange={(e) => setSelectedSpeed(e.target.value)}
                  className="w-full bg-black/50 border border-neutral-700 rounded-2xl px-5 py-2.5 text-white appearance-none focus:outline-none focus:border-white/30 cursor-pointer transition-colors"
                >
                  {speeds.map(speed => (
                    <option key={speed} value={speed}>{speed}</option>
                  ))}
                </select>
                <ChevronDownIcon className="absolute right-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white pointer-events-none" />
              </div>
            </div>
          </div>

          {/* Model Section */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <span className="text-sm font-medium text-neutral-400">MODEL</span>
            </div>
            <div className="relative">
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="w-full bg-black/50 border border-neutral-700 rounded-2xl px-5 py-2.5 text-white appearance-none focus:outline-none focus:border-white/30 cursor-pointer transition-colors"
              >
                {models.map(model => (
                  <option key={model} value={model}>{model}</option>
                ))}
              </select>
              <ChevronDownIcon className="absolute right-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-green-400 pointer-events-none" />
            </div>
          </div>

          {/* Avatar Section */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span className="text-sm font-medium text-neutral-400">AVATAR</span>
            </div>
            
            <div className="border-2 border-dashed border-neutral-700 rounded-2xl p-3 text-center hover:border-white/30 transition-colors cursor-pointer bg-black/30 flex items-center justify-center space-x-3">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span className="text-white text-sm font-medium">Upload Image</span>
            </div>

          </div>

          {/* Privacy Section */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <span className="text-sm font-medium text-neutral-400">PRIVACY</span>
            </div>
            <div className="relative">
              <select
                value={selectedPrivacy}
                onChange={(e) => setSelectedPrivacy(e.target.value)}
                className="w-full bg-black/50 border border-neutral-700 rounded-2xl px-5 py-2.5 text-white appearance-none focus:outline-none focus:border-white/30 cursor-pointer transition-colors"
              >
                {privacyOptions.map(option => (
                  <option key={option} value={option}>{option}</option>
                ))}
              </select>
              <div className="absolute right-12 top-1/2 transform -translate-y-1/2">
                <div className="w-2 h-2 bg-white rounded-full"></div>
              </div>
              <ChevronDownIcon className="absolute right-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-green-400 pointer-events-none" />
            </div>
          </div>

            </div>

            {/* Navigation Buttons - positioned relative to form */}
            <div className="flex items-center justify-center space-x-4 mt-8">
                <button className="bg-neutral-800/90 hover:bg-neutral-700 text-neutral-300 hover:text-white font-medium px-8 py-4 rounded-full transition-colors flex items-center space-x-3 backdrop-blur-sm">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 19l-7-7 7-7" />
                  </svg>
                  <span>Back</span>
                </button>
                
                <button className="bg-white hover:bg-gray-200 text-black font-medium px-10 py-4 rounded-full transition-colors flex items-center space-x-3">
                  <span className="text-lg">Next</span>
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5l7 7-7 7" />
                  </svg>
                  <div className="ml-1">
                    <div className="text-xs opacity-75 uppercase tracking-wide">BEHAVIOR</div>
                  </div>
                </button>
            </div>
          </div>
        </div>
      </div>

      {/* Right Agent Preview Panel */}
      <div className="w-96 bg-black flex flex-col p-6">
        <div className="flex-1 flex flex-col items-center justify-center">
          {/* Preview Container */}
          <div className="bg-neutral-900/80 rounded-2xl p-12 flex flex-col items-center w-full h-[500px] border border-neutral-700/50">
            <div className="mb-8">
              <h2 className="text-sm font-medium text-neutral-400 text-center">AGENT PREVIEW</h2>
            </div>
            
            {/* Microphone Button */}
            <div className="w-20 h-20 rounded-full bg-black border-2 border-white flex items-center justify-center mb-12 hover:bg-neutral-900 transition-colors cursor-pointer">
              <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </div>
            
            {/* Conversation ID */}
            <div className="text-center">
              <div className="text-sm font-medium text-neutral-300 mb-2">Conversation ID</div>
              <div className="text-xs text-neutral-500 font-mono">KDyKbfjklGAJEwaKDnyZ</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateNewPage;