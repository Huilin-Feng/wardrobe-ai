import { useState } from 'react'
import RecommendPage from './pages/RecommendPage'
import WardrobePage from './pages/WardrobePage'

const TABS = [
  { id: 'wardrobe', label: 'Wardrobe' },
  { id: 'recommend', label: 'Get dressed' },
]

export default function App() {
  const [tab, setTab] = useState('wardrobe')

  return (
    <div className="min-h-screen bg-stone-100 text-stone-900">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4">
          <h1 className="text-lg font-semibold">AI Wardrobe Assistant</h1>
          <nav className="flex gap-1" aria-label="Main">
            {TABS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setTab(item.id)}
                aria-current={tab === item.id ? 'page' : undefined}
                className={`rounded-md px-3 py-1.5 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-stone-900 ${
                  tab === item.id ? 'bg-stone-900 text-white' : 'text-stone-600 hover:bg-stone-100'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-6 py-8">
        {tab === 'wardrobe' ? <WardrobePage /> : <RecommendPage />}
      </main>
    </div>
  )
}