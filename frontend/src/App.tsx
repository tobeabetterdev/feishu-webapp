import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import OrderComparison from './pages/OrderComparison'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/order-comparison" element={<OrderComparison />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App