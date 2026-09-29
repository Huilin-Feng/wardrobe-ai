import { useEffect, useState } from 'react'
import { listClothing } from './api/client'

export default function App() {
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    listClothing()
      .then(setItems)
      .catch((err) => setError(err.message))
  }, [])

  return (
    <div className="min-h-screen bg-stone-50 p-8">
      <h1 className="text-3xl font-semibold text-stone-800">AI Wardrobe Assistant</h1>
      {error && <p className="mt-4 text-red-600">Error: {error}</p>}
      <p className="mt-4 text-stone-600">{items.length} items in wardrobe</p>
    </div>
  )
}