import './App.css'
import DealsPage from './components/DealsPage'
import BottomNav from './components/BottomNav'

function App() {
  return (
    <div className="app-shell">
      <DealsPage />
      <BottomNav active="deals" />
    </div>
  )
}

export default App
