import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Agent from './components/Agent'
import CreateNewPage from './components/CreateNewPage'

function App() {
  const [currentPage, setCurrentPage] = useState<'agent' | 'create-new'>('agent')

  const renderCurrentPage = () => {
    switch (currentPage) {
      case 'create-new':
        return <CreateNewPage />
      case 'agent':
      default:
        return <Agent />
    }
  }

  return (
    <div className="flex h-screen bg-black text-white">
      <Sidebar onNavigate={setCurrentPage} />
      <div className="flex-1">
        {renderCurrentPage()}
      </div>
    </div>
  )
}

export default App