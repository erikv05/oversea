import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Agent from './components/Agent'
import CreateNewPage from './components/CreateNewPage'
import MyAgentsPage from './components/MyAgentsPage'

function App() {
  const [currentPage, setCurrentPage] = useState<'agent' | 'create-new' | 'agent-detail'>('agent')
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null)

  const handleNavigate = (page: 'agent' | 'create-new') => {
    setCurrentPage(page)
    if (page !== 'agent') {
      setSelectedAgentId(null)
    }
  }

  const handleAgentSelect = (agentId: string) => {
    setSelectedAgentId(agentId)
    setCurrentPage('agent-detail')
  }

  const handleAgentCreated = () => {
    // Navigate back to agents list after creation
    setCurrentPage('agent')
  }

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'create-new':
        return <CreateNewPage onAgentCreated={handleAgentCreated} />
      case 'agent':
        return <MyAgentsPage onNavigate={handleNavigate} onAgentSelect={handleAgentSelect} />
      case 'agent-detail':
        return <Agent agentId={selectedAgentId} onBack={() => setCurrentPage('agent')} />
      default:
        return <MyAgentsPage onNavigate={handleNavigate} onAgentSelect={handleAgentSelect} />
    }
  }

  return (
    <div className="flex h-screen bg-black text-white">
      <Sidebar onNavigate={handleNavigate} currentPage={currentPage === 'agent-detail' ? 'agent' : currentPage} />
      <div className="flex-1">
        {renderCurrentPage()}
      </div>
    </div>
  )
}

export default App