import React from 'react';
import { PlusIcon } from '@heroicons/react/24/outline';

interface Agent {
  id: string;
  name: string;
  agentId: string;
  conversations: number;
  minutesSpoken: number;
  knowledgeResources: number;
}

interface MyAgentsPageProps {
  onNavigate: (page: "agent" | "create-new") => void;
  onAgentSelect: (agentId: string) => void;
}

const MyAgentsPage: React.FC<MyAgentsPageProps> = ({ onNavigate, onAgentSelect }) => {
  // Sample agents data
  const agents: Agent[] = [
    {
      id: '1',
      name: 'Bozidar',
      agentId: 'Bozidar-w_h1TK56Y0iAUA8w3RMUG',
      conversations: 3,
      minutesSpoken: 1.1,
      knowledgeResources: 0
    },
    {
      id: '2',
      name: 'Untitled Agent',
      agentId: 'Untitled-Agent-aWpxhFTF__QiioF0kffGz',
      conversations: 2,
      minutesSpoken: 0,
      knowledgeResources: 0
    }
  ];


  return (
    <div className="flex-1 bg-black p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-medium text-white">My Agents</h1>
        <button
          onClick={() => onNavigate("create-new")}
          className="flex items-center space-x-2 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/20 text-blue-400 px-4 py-2 rounded-full transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          <span>Create New Agent</span>
        </button>
      </div>

      {/* Agent Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {agents.map((agent) => (
          <div key={agent.id} className="bg-neutral-900/80 rounded-3xl p-6 border border-neutral-800/30 flex flex-col">
            {/* Agent Header */}
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-medium text-white">{agent.name}</h3>
              <div className="flex items-center space-x-2">
                <button 
                  onClick={() => onAgentSelect(agent.id)}
                  className="flex items-center space-x-1.5 px-3 py-2 bg-blue-600/30 hover:bg-blue-600/40 border border-blue-500/20 rounded-full transition-colors group"
                >
                  <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                  </svg>
                  <span className="text-sm font-medium text-blue-400">Talk</span>
                </button>
                <button className="p-2 hover:bg-neutral-800 rounded-full transition-colors">
                  <svg className="w-5 h-5 text-neutral-400" fill="none" viewBox="0 0 24 24">
                    <circle cx="5" cy="12" r="2" fill="currentColor" />
                    <circle cx="12" cy="12" r="2" fill="currentColor" />
                    <circle cx="19" cy="12" r="2" fill="currentColor" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Agent ID */}
            <div className="flex items-center space-x-2 mb-6">
              <svg className="w-4 h-4 text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
              <span className="text-sm text-neutral-500 font-mono truncate">{agent.agentId}</span>
            </div>

            {/* Stats */}
            <div className="space-y-3 mb-6 flex-1">
              <div className="flex items-center space-x-3">
                <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span className="text-sm text-neutral-300">{agent.conversations} conversations</span>
              </div>
              
              <div className="flex items-center space-x-3">
                <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-sm text-neutral-300">{agent.minutesSpoken} minutes spoken</span>
              </div>
              
              <div className="flex items-center space-x-3">
                <svg className="w-5 h-5 text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="text-sm text-neutral-300">{agent.knowledgeResources} knowledge resources added</span>
              </div>
            </div>

            {/* View Agent Button */}
            <button 
              onClick={() => onAgentSelect(agent.id)}
              className="w-full bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/20 text-blue-400 font-medium py-2.5 rounded-full transition-colors flex items-center justify-center space-x-2"
            >
              <span>View Agent</span>
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MyAgentsPage;