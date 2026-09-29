import WardrobePage from './pages/WardrobePage'

export default function App() {
  return (
    <div className="min-h-screen bg-stone-100 text-stone-900">
      <header className="border-b border-stone-200 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-4">
          <h1 className="text-lg font-semibold">AI Wardrobe Assistant</h1>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <WardrobePage />
      </main>
    </div>
  )
}