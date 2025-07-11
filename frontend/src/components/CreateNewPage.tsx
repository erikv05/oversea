import React, { useState } from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';
import { API_URL } from '../config';

interface CreateNewPageProps {
  onAgentCreated?: () => void;
}

const CreateNewPage: React.FC<CreateNewPageProps> = ({ onAgentCreated }) => {
  const [agentName, setAgentName] = useState('Untitled Agent');
  const [selectedVoice, setSelectedVoice] = useState('Vincent');
  const [selectedSpeed, setSelectedSpeed] = useState('1.0x');
  const [selectedModel, setSelectedModel] = useState('Play 2.0 (Most Stable)');
  const [selectedPrivacy, setSelectedPrivacy] = useState('Public');
  const [currentStep, setCurrentStep] = useState('overview');
  const [agentGreeting, setAgentGreeting] = useState('');
  const [agentPrompt, setAgentPrompt] = useState('');
  const [selectedBehavior, setSelectedBehavior] = useState('');
  const [selectedLLM, setSelectedLLM] = useState('GPT 4o');
  const [customKnowledge, setCustomKnowledge] = useState('');
  const [guardrailsEnabled, setGuardrailsEnabled] = useState(false);
  const [currentDateEnabled, setCurrentDateEnabled] = useState(true);
  const [callerInfoEnabled, setCallerInfoEnabled] = useState(true);
  const [selectedTimezone, setSelectedTimezone] = useState('(GMT-08:00) Pacific Time (US & Canada)');

  const voices = ['Vincent', 'Alice', 'Bob', 'Emma'];
  const speeds = ['0.5x', '0.75x', '1.0x', '1.25x', '1.5x', '2.0x'];
  const models = ['Play 2.0 (Most Stable)', 'Play 3.0 (Beta)', 'GPT-4'];
  const privacyOptions = ['Public', 'Private', 'Unlisted'];
  const llmOptions = ['GPT 4o', 'GPT 3.5 Turbo', 'Claude 3', 'Gemini Pro'];
  const timezones = [
    '(GMT-08:00) Pacific Time (US & Canada)',
    '(GMT-05:00) Eastern Time (US & Canada)',
    '(GMT+00:00) UTC',
    '(GMT+01:00) Central European Time',
    '(GMT+09:00) Japan Standard Time'
  ];


  const steps = [
    { id: 'overview', label: 'Overview', completed: true },
    { id: 'personality', label: 'Personality', completed: false },
    { id: 'knowledge', label: 'Knowledge', completed: false },
    { id: 'actions', label: 'Actions', completed: false },
    { id: 'deploy-phone', label: 'Deploy • Phone', completed: false },
  ];

  const getCurrentStepIndex = () => steps.findIndex(step => step.id === currentStep);
  
  const goToPreviousStep = () => {
    const currentIndex = getCurrentStepIndex();
    if (currentIndex > 0) {
      setCurrentStep(steps[currentIndex - 1].id);
    }
  };

  const goToNextStep = () => {
    const currentIndex = getCurrentStepIndex();
    if (currentIndex < steps.length - 1) {
      setCurrentStep(steps[currentIndex + 1].id);
    }
  };

  const getPreviousStepLabel = () => {
    const currentIndex = getCurrentStepIndex();
    return currentIndex > 0 ? steps[currentIndex - 1].label : null;
  };

  const getNextStepLabel = () => {
    const currentIndex = getCurrentStepIndex();
    return currentIndex < steps.length - 1 ? steps[currentIndex + 1].label : null;
  };

  const saveAgent = async () => {
    try {
      const agentData = {
        name: agentName,
        voice: selectedVoice,
        speed: selectedSpeed,
        greeting: agentGreeting,
        system_prompt: agentPrompt,
        behavior: selectedBehavior,
        llm_model: selectedLLM,
        custom_knowledge: customKnowledge,
        guardrails_enabled: guardrailsEnabled,
        current_date_enabled: currentDateEnabled,
        caller_info_enabled: callerInfoEnabled,
        timezone: selectedTimezone
      };

      const response = await fetch(`${API_URL}/api/agents/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(agentData),
      });

      if (response.ok) {
        const newAgent = await response.json();
        console.log('Agent created:', newAgent);
        if (onAgentCreated) {
          onAgentCreated();
        }
        // You could also navigate back to the agents list here
      } else {
        console.error('Failed to create agent');
      }
    } catch (error) {
      console.error('Error creating agent:', error);
    }
  };

  const getStepIcon = (stepId: string, isActive: boolean) => {
    const gradientId = `icon-gradient-${stepId}`;
    const fillColor = isActive ? `url(#${gradientId})` : 'currentColor';
    
    switch (stepId) {
      case 'overview':
        return (
          <svg className="w-6 h-6" fill={fillColor} viewBox="0 0 24 24">
            {isActive && (
              <defs>
                <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#60a5fa" />
                  <stop offset="100%" stopColor="#3b82f6" />
                </linearGradient>
              </defs>
            )}
            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
          </svg>
        );
      case 'personality':
        return (
          <svg className="w-6 h-6" fill={fillColor} viewBox="0 0 24 24">
            {isActive && (
              <defs>
                <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#60a5fa" />
                  <stop offset="100%" stopColor="#3b82f6" />
                </linearGradient>
              </defs>
            )}
            <path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z"/>
          </svg>
        );
      case 'knowledge':
        return (
          <svg className="w-6 h-6" fill="none" stroke={isActive ? `url(#${gradientId})` : 'currentColor'} strokeWidth={2} viewBox="0 0 24 24">
            {isActive && (
              <defs>
                <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#60a5fa" />
                  <stop offset="100%" stopColor="#3b82f6" />
                </linearGradient>
              </defs>
            )}
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        );
      case 'actions':
        return (
          <svg className="w-6 h-6" fill={fillColor} viewBox="0 0 24 24">
            {isActive && (
              <defs>
                <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#60a5fa" />
                  <stop offset="100%" stopColor="#3b82f6" />
                </linearGradient>
              </defs>
            )}
            <path d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        );
      case 'deploy-phone':
        return (
          <svg className="w-6 h-6" fill={fillColor} viewBox="0 0 24 24">
            {isActive && (
              <defs>
                <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#60a5fa" />
                  <stop offset="100%" stopColor="#3b82f6" />
                </linearGradient>
              </defs>
            )}
            <path d="M20 15.5c-1.25 0-2.45-.2-3.57-.57a1.02 1.02 0 00-1.02.24l-2.2 2.2a15.074 15.074 0 01-6.59-6.59l2.2-2.21a.96.96 0 00.25-1A11.36 11.36 0 018.5 4c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1 0 9.39 7.61 17 17 17 .55 0 1-.45 1-1v-3.5c0-.55-.45-1-1-1zM5.03 5h1.5c.07.88.22 1.75.45 2.58l-1.2 1.21c-.4-1.21-.66-2.47-.75-3.79zM19 18.97c-1.32-.09-2.6-.35-3.8-.76l1.2-1.2c.85.24 1.72.39 2.6.45v1.51z"/>
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen bg-black text-white">
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">

        {/* Navigation Panel */}
        <div className="bg-black border-b border-neutral-800/30 pt-6">
          <div className="flex items-center justify-center px-6 py-4">
            <div className="bg-blue-950/30 border border-blue-900/30 rounded-full p-2 flex items-center space-x-1">
              {steps.map((step, index) => (
                <div 
                  key={step.id}
                  className={`flex items-center space-x-2 px-3 py-2 rounded-full cursor-pointer transition-all ${
                    step.id === currentStep 
                      ? 'bg-blue-600/30' 
                      : 'hover:bg-neutral-800/60 text-neutral-300'
                  }`}
                  onClick={() => setCurrentStep(step.id)}
                >
                  <div>
                    {getStepIcon(step.id, true)}
                  </div>
                  <span className="text-sm font-medium text-blue-400">{step.label}</span>
                  {step.completed && step.id === 'overview' && (
                    <svg className="w-4 h-4" fill="url(#nav-gradient-check)" viewBox="0 0 20 20">
                      <defs>
                        <linearGradient id="nav-gradient-check" x1="0%" y1="0%" x2="100%" y2="0%">
                          <stop offset="0%" stopColor="#60a5fa" />
                          <stop offset="100%" stopColor="#3b82f6" />
                        </linearGradient>
                      </defs>
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Content Container */}
        <div className="flex-1 flex overflow-hidden">
          {/* Main content container */}
          <div className="flex-1 overflow-y-auto p-6 relative pb-24">
            <div className="max-w-lg mx-auto relative">
            {/* Form Container */}
            {currentStep === 'overview' ? (
            <div className="bg-neutral-900/80 rounded-2xl p-6 space-y-5 border border-neutral-800/30">
          
          {/* Name Section */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <div className="w-6 h-6 rounded-full bg-neutral-600 flex items-center justify-center">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
              </div>
              <span className="text-sm font-medium text-neutral-400">AGENT DISPLAY NAME</span>
            </div>
            <input
              type="text"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              className="w-full bg-black/50 border border-neutral-800/50 rounded-2xl px-5 py-2.5 text-white placeholder-neutral-400 focus:outline-none focus:border-white/20 transition-colors"
              placeholder="Enter agent display name"
            />
          </div>

          {/* Voice Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
                <span className="text-sm font-medium text-neutral-400">VOICE STYLE</span>
              </div>
              <div className="flex items-center space-x-2">
                <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5.636 5.636a9 9 0 1012.728 0M12 3v9" />
                </svg>
                <span className="text-sm font-medium text-neutral-400">SPEAKING SPEED</span>
              </div>
            </div>
            
            <div className="flex space-x-4">
              <div className="flex-1 relative">
                <select
                  value={selectedVoice}
                  onChange={(e) => setSelectedVoice(e.target.value)}
                  className="w-full bg-black/50 border border-neutral-800/50 rounded-2xl px-5 py-2.5 text-white appearance-none focus:outline-none focus:border-white/20 cursor-pointer transition-colors"
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
                  className="w-full bg-black/50 border border-neutral-800/50 rounded-2xl px-5 py-2.5 text-white appearance-none focus:outline-none focus:border-white/20 cursor-pointer transition-colors"
                >
                  {speeds.map(speed => (
                    <option key={speed} value={speed}>{speed}</option>
                  ))}
                </select>
                <ChevronDownIcon className="absolute right-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white pointer-events-none" />
              </div>
            </div>
          </div>


          {/* Behavior Instructions Section */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="text-sm font-medium text-neutral-400">BEHAVIOR INSTRUCTIONS</span>
              <span className="text-xs text-neutral-500 ml-2">Advanced Instructions</span>
            </div>
            <p className="text-sm text-neutral-500">Define how your AI agent should act and communicate during conversations with users.</p>
            <textarea
              value={agentPrompt}
              onChange={(e) => setAgentPrompt(e.target.value)}
              placeholder="e.g. You are a helpful customer service representative. Always provide accurate answers based on available information. Never fabricate or guess at information you don't have."
              className="w-full h-40 bg-black/50 border border-neutral-800/50 rounded-2xl px-5 py-4 text-white placeholder-neutral-600 focus:outline-none focus:border-white/20 transition-colors resize-none"
            />
            <div className="text-xs text-neutral-500">{agentPrompt.length}/10000</div>
          </div>

          {/* Initial Message Section */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
              <span className="text-sm font-medium text-neutral-400">INITIAL MESSAGE</span>
            </div>
            <p className="text-sm text-neutral-500">This message will be spoken by your agent at the beginning of each call.</p>
            <textarea
              value={agentGreeting}
              onChange={(e) => setAgentGreeting(e.target.value)}
              placeholder="e.g. Hello! How can I help you today?"
              className="w-full h-32 bg-black/50 border border-neutral-800/50 rounded-2xl px-5 py-4 text-white placeholder-neutral-600 focus:outline-none focus:border-white/20 transition-colors resize-none"
            />
            <div className="text-xs text-neutral-500">{agentGreeting.length}/250</div>
          </div>

            </div>
            ) : currentStep === 'personality' ? (
              <div className="bg-neutral-900/80 rounded-2xl p-6 space-y-6 border border-neutral-800/30">
                {/* Agent Behavior Section */}
                <div className="space-y-3">
                  <div className="flex items-center space-x-2">
                    <svg className="w-5 h-5 text-neutral-400" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
                    </svg>
                    <span className="text-sm font-medium text-neutral-400">TONE PRESET</span>
                  </div>
                  
                  <div className="space-y-3">
                    <div 
                      className={`border rounded-2xl p-4 cursor-pointer transition-all ${
                        selectedBehavior === 'professional' 
                          ? 'border-white bg-white/10' 
                          : 'border-neutral-800/50 hover:border-neutral-700'
                      }`}
                      onClick={() => setSelectedBehavior('professional')}
                    >
                      <h3 className="text-white font-medium mb-1">Professional Use Case</h3>
                      <p className="text-sm text-neutral-400">Designed for formal, courteous interactions while maintaining focus and being helpful.</p>
                    </div>
                    
                    <div 
                      className={`border rounded-2xl p-4 cursor-pointer transition-all ${
                        selectedBehavior === 'character' 
                          ? 'border-white bg-white/10' 
                          : 'border-neutral-800/50 hover:border-neutral-700'
                      }`}
                      onClick={() => setSelectedBehavior('character')}
                    >
                      <h3 className="text-white font-medium mb-1">Character Use Case</h3>
                      <p className="text-sm text-neutral-400">Set up to embody and maintain a specific character or persona.</p>
                    </div>
                    
                    <div 
                      className={`border rounded-2xl p-4 cursor-pointer transition-all ${
                        selectedBehavior === 'chatty' 
                          ? 'border-white bg-white/10' 
                          : 'border-neutral-800/50 hover:border-neutral-700'
                      }`}
                      onClick={() => setSelectedBehavior('chatty')}
                    >
                      <h3 className="text-white font-medium mb-1">Super Chatty</h3>
                      <p className="text-sm text-neutral-400">Perfect for relaxed, friendly chats as if speaking with a close companion.</p>
                    </div>
                    
                    <div 
                      className={`border rounded-2xl p-4 cursor-pointer transition-all ${
                        selectedBehavior === 'concise' 
                          ? 'border-white bg-white/10' 
                          : 'border-neutral-800/50 hover:border-neutral-700'
                      }`}
                      onClick={() => setSelectedBehavior('concise')}
                    >
                      <h3 className="text-white font-medium mb-1">Concise & Direct</h3>
                      <p className="text-sm text-neutral-400">Delivers quick, straightforward answers without unnecessary details.</p>
                    </div>
                    
                    <div 
                      className={`border rounded-2xl p-4 cursor-pointer transition-all ${
                        selectedBehavior === 'empathetic' 
                          ? 'border-white bg-white/10' 
                          : 'border-neutral-800/50 hover:border-neutral-700'
                      }`}
                      onClick={() => setSelectedBehavior('empathetic')}
                    >
                      <h3 className="text-white font-medium mb-1">Empathetic & Supportive</h3>
                      <p className="text-sm text-neutral-400">Provides caring, compassionate replies with emotional intelligence.</p>
                    </div>
                  </div>
                </div>
              </div>
            ) : currentStep === 'knowledge' ? (
              <div className="bg-neutral-900/80 rounded-2xl p-6 space-y-6 border border-neutral-800/30">
                {/* Agent LLM Section */}
                <div className="space-y-3">
                  <h2 className="text-xl font-medium text-white">Agent LLM</h2>
                  <p className="text-sm text-neutral-400">
                    Choose the AI model that will drive your agent's conversational abilities. 
                    <a href="#" className="text-blue-400 hover:text-blue-300 ml-1">Learn more</a>
                  </p>
                  <div className="relative">
                    <select
                      value={selectedLLM}
                      onChange={(e) => setSelectedLLM(e.target.value)}
                      className="w-full bg-black/50 border border-neutral-800/50 rounded-2xl px-5 py-3 text-blue-400 appearance-none focus:outline-none focus:border-white/20 cursor-pointer transition-colors"
                    >
                      {llmOptions.map(llm => (
                        <option key={llm} value={llm}>{llm}</option>
                      ))}
                    </select>
                    <ChevronDownIcon className="absolute right-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white pointer-events-none" />
                  </div>
                </div>

                {/* Custom Knowledge Section */}
                <div className="space-y-3">
                  <h2 className="text-xl font-medium text-white">Custom Knowledge</h2>
                  <p className="text-sm text-neutral-400">Provide specialized information for your agent to reference.</p>
                  
                  {/* Text Input */}
                  <div className="space-y-3">
                    <div className="flex items-center space-x-2">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                      <span className="text-sm font-medium text-white">TEXT INPUT</span>
                    </div>
                    <p className="text-sm text-neutral-500">Enter key details and facts your agent needs to understand</p>
                    <textarea
                      value={customKnowledge}
                      onChange={(e) => setCustomKnowledge(e.target.value)}
                      placeholder="e.g. The more specific details you provide, the better your agent will meet your needs. For business use, include information like operating hours, FAQ responses, service guidelines, product details, etc."
                      className="w-full h-40 bg-black/50 border border-neutral-800/50 rounded-2xl px-5 py-4 text-white placeholder-neutral-600 focus:outline-none focus:border-white/20 transition-colors resize-none"
                    />
                    <div className="text-xs text-neutral-500">{customKnowledge.length}/100000</div>
                  </div>

                  {/* Files Upload */}
                  <div className="space-y-3 mt-6">
                    <div className="flex items-center space-x-2">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span className="text-sm font-medium text-white">FILES</span>
                    </div>
                    <p className="text-sm text-neutral-500">Add a maximum of 10 reference files. Compact files work more efficiently.</p>
                    <button className="w-full bg-black/50 border border-neutral-800/50 rounded-2xl px-5 py-3 text-blue-400 hover:border-white/20 transition-colors flex items-center justify-center space-x-2">
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                      </svg>
                      <span>Upload knowledge files</span>
                    </button>
                  </div>
                </div>

                {/* Guardrails Section */}
                <div className="space-y-3 mt-6">
                  <div className="flex items-center space-x-2">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-sm font-medium text-white">GUARDRAILS</span>
                  </div>
                  <p className="text-sm text-neutral-400">Restrict agent responses to only use information from the provided knowledge base?</p>
                  <label className="flex items-center space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={guardrailsEnabled}
                      onChange={(e) => setGuardrailsEnabled(e.target.checked)}
                      className="w-5 h-5 rounded border-neutral-600 bg-black/50 text-blue-400 focus:ring-blue-400"
                    />
                    <span className="text-sm text-neutral-300">Yes, limit responses to knowledge base content only.</span>
                  </label>
                </div>

                {/* Dynamic Context Section */}
                <div className="space-y-3 mt-6">
                  <div className="flex items-center space-x-2">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-sm font-medium text-white">DYNAMIC CONTEXT</span>
                  </div>
                  <p className="text-sm text-neutral-400">Enhance your agent with real-time contextual information.</p>

                  {/* Current Date & Time */}
                  <div className={`border rounded-2xl p-4 transition-all ${currentDateEnabled ? 'border-blue-400 bg-blue-400/10' : 'border-neutral-800/50'}`}>
                    <label className="flex items-start cursor-pointer">
                      <input
                        type="checkbox"
                        checked={currentDateEnabled}
                        onChange={(e) => setCurrentDateEnabled(e.target.checked)}
                        className="mt-1 w-5 h-5 rounded border-neutral-600 bg-black/50 text-blue-400 focus:ring-blue-400"
                      />
                      <div className="ml-3 flex-1">
                        <h3 className="text-white font-medium mb-1">Current Date & Time</h3>
                        <p className="text-sm text-neutral-400 mb-3">Provide your agent with present date and time awareness</p>
                        {currentDateEnabled && (
                          <div className="space-y-2">
                            <label className="text-sm text-neutral-400">TIMEZONE</label>
                            <div className="relative">
                              <select
                                value={selectedTimezone}
                                onChange={(e) => setSelectedTimezone(e.target.value)}
                                className="w-full bg-black/50 border border-neutral-800/50 rounded-xl px-4 py-2 text-white appearance-none focus:outline-none focus:border-white/20 cursor-pointer transition-colors"
                              >
                                {timezones.map(tz => (
                                  <option key={tz} value={tz}>{tz}</option>
                                ))}
                              </select>
                              <ChevronDownIcon className="absolute right-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white pointer-events-none" />
                            </div>
                          </div>
                        )}
                      </div>
                    </label>
                  </div>

                  {/* Caller Information */}
                  <div className={`border rounded-2xl p-4 transition-all ${callerInfoEnabled ? 'border-blue-400 bg-blue-400/10' : 'border-neutral-800/50'}`}>
                    <label className="flex items-start cursor-pointer">
                      <input
                        type="checkbox"
                        checked={callerInfoEnabled}
                        onChange={(e) => setCallerInfoEnabled(e.target.checked)}
                        className="mt-1 w-5 h-5 rounded border-neutral-600 bg-black/50 text-blue-400 focus:ring-blue-400"
                      />
                      <div className="ml-3 flex-1">
                        <h3 className="text-white font-medium mb-1">Caller Information</h3>
                        <p className="text-sm text-neutral-400">Include caller contact details like phone or email if accessible</p>
                      </div>
                    </label>
                  </div>
                </div>
              </div>
            ) : currentStep === 'deploy-phone' ? (
              <div className="bg-neutral-900/80 rounded-2xl p-6 space-y-6 border border-neutral-800/30">
                {/* Deploy Agent To Phone Header */}
                <div className="space-y-3">
                  <div className="flex items-center space-x-3">
                    <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                    </svg>
                    <h2 className="text-2xl font-medium text-white">Deploy Agent To Phone</h2>
                  </div>
                  <p className="text-sm text-neutral-400">
                    Monthly fee is $2.00 for this number, plus additional costs for call minutes. 
                    <a href="#" className="text-white underline ml-1">View detailed pricing information.</a>
                  </p>
                </div>

                {/* Upgrade Notice Banner */}
                <div className="bg-yellow-900/20 border border-yellow-600/50 rounded-2xl p-4 flex items-start space-x-3">
                  <div className="relative w-12 h-12 rounded-full bg-yellow-600/20 flex items-center justify-center flex-shrink-0">
                    <svg className="w-6 h-6 text-yellow-500" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
                    </svg>
                    <span className="absolute -bottom-1 -right-1 bg-yellow-500 text-black text-xs font-bold w-4 h-4 rounded-full flex items-center justify-center">!</span>
                  </div>
                  <div className="flex-1">
                    <p className="text-white">
                      Phone number deployment requires a paid subscription. 
                      <a href="#" className="underline ml-1">Upgrade now to enable this feature.</a>
                    </p>
                  </div>
                </div>

                {/* Add Phone Number Button */}
                <button className="w-full bg-black/50 border border-neutral-800/50 rounded-2xl px-5 py-2.5 text-neutral-400 hover:border-white/20 transition-colors flex items-center justify-center space-x-3">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                  <span>Add a phone number</span>
                </button>

                {/* Call Transfer Section */}
                <div className="space-y-4 mt-8">
                  <div className="flex items-center space-x-3">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                    </svg>
                    <h3 className="text-xl font-medium text-white">Call Transfer</h3>
                  </div>
                  <p className="text-sm text-neutral-400">Get a phone number to activate call forwarding capabilities.</p>
                  
                  <button className="w-full bg-black/50 border border-neutral-800/50 rounded-2xl px-5 py-2.5 text-neutral-400 hover:border-white/20 transition-colors flex items-center justify-center space-x-3">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                    </svg>
                    <span>Add Transfer Number</span>
                  </button>
                </div>
              </div>
            ) : null}

            </div>
          </div>
        </div>

        {/* Fixed Navigation Buttons - Only spans main content area */}
        <div className="bg-neutral-950/80 backdrop-blur-sm border-t border-neutral-800/30 p-4">
          <div className="flex items-center justify-between px-6">
            {/* Save Agent Button */}
            <button 
              onClick={saveAgent}
              className="bg-green-600/30 hover:bg-green-600/40 border border-green-500/20 text-green-400 font-medium px-6 py-2.5 rounded-2xl transition-all duration-200"
            >
              Save Agent
            </button>
            
            <div className="flex items-center space-x-3">
            {getPreviousStepLabel() && (
              <button 
                onClick={goToPreviousStep}
                className="bg-neutral-900/40 hover:bg-neutral-800/60 border border-neutral-800/30 text-neutral-300 hover:text-white font-medium px-4 py-2.5 rounded-2xl transition-all duration-200 flex items-center space-x-2 w-40"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                <div className="text-left flex-1">
                  <div className="text-sm font-medium leading-tight text-blue-400">Back</div>
                  <div className="text-xs text-neutral-500 truncate leading-tight">{getPreviousStepLabel()}</div>
                </div>
              </button>
            )}
            
            {getNextStepLabel() && (
              <button 
                onClick={goToNextStep}
                className="bg-blue-600/30 hover:bg-blue-600/40 border border-blue-500/20 text-white font-medium px-4 py-2.5 rounded-2xl transition-all duration-200 flex items-center space-x-2 w-40"
              >
                <div className="text-left flex-1">
                  <div className="text-sm font-medium leading-tight text-blue-400">Next</div>
                  <div className="text-xs text-blue-300 truncate leading-tight">{getNextStepLabel()}</div>
                </div>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </button>
            )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CreateNewPage;