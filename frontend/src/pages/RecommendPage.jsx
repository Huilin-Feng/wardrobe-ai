import { useState } from 'react'
import GarmentImage from '../components/GarmentImage'
import { describeError, recommendOutfit } from '../api/client'

// Values match the backend; labels are what users see.
const OCCASIONS = [
  { value: 'casual', label: 'Everyday' },
  { value: 'work', label: 'Work' },
  { value: 'date', label: 'Date' },
  { value: 'formal', label: 'Formal event' },
  { value: 'workout', label: 'Workout' },
]

function ScoreBar({ label, value }) {
  const percent = Math.round(value * 100)
  return (
    <div>
      <div className="flex justify-between text-xs">
        <span className="text-stone-500">{label}</span>
        <span className="tabular-nums text-stone-700">{percent}</span>
      </div>
      <div
        className="mt-1 h-1.5 rounded-full bg-stone-200"
        role="meter"
        aria-label={label}
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-full rounded-full bg-stone-800" style={{ width: `${percent}%` }} />
      </div>
    </div>
  )
}

function OutfitCard({ outfit, recommended }) {
  return (
    <article
      className={`rounded-lg border bg-white p-4 ${
        recommended ? 'border-stone-900 ring-1 ring-stone-900' : 'border-stone-200'
      }`}
    >
      <div className="flex min-h-6 items-center justify-between gap-2">
        {recommended ? (
          <span className="rounded-full bg-stone-900 px-2.5 py-0.5 text-xs font-medium text-white">
            Recommended
          </span>
        ) : (
          <span />
        )}
        <span className="text-sm tabular-nums text-stone-500">
          Overall {Math.round(outfit.total * 100)}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-4 gap-2">
        {outfit.items.map((item) => (
          <figure key={item.id} className="min-w-0">
            <GarmentImage item={item} className="rounded-md border border-stone-200" />
            <figcaption className="mt-1 truncate text-xs capitalize text-stone-600">
              {item.color} {item.category}
            </figcaption>
          </figure>
        ))}
      </div>

      {outfit.reason && (
        <p className="mt-4 text-sm leading-relaxed text-stone-700">{outfit.reason}</p>
      )}

      {/* Ordered by weight: occasion counts most. */}
      <div className="mt-4 space-y-2">
        <ScoreBar label="Occasion" value={outfit.occasion} />
        <ScoreBar label="Temperature" value={outfit.temperature} />
        <ScoreBar label="Color" value={outfit.color} />
      </div>
    </article>
  )
}

export default function RecommendPage() {
  const [city, setCity] = useState('')
  const [occasion, setOccasion] = useState('casual')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)

  async function handleSubmit(event) {
    event.preventDefault() // stop the browser from reloading the page
    if (!city.trim()) return

    setLoading(true)
    setError(null)
    try {
      setResult(await recommendOutfit(city.trim(), occasion))
    } catch (err) {
      setResult(null)
      setError(describeError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <section>
      <h2 className="text-xl font-semibold text-stone-900">Get dressed</h2>
      <p className="mt-1 text-sm text-stone-500">
        Outfits are built from your wardrobe and today's weather where you are.
      </p>

      <form onSubmit={handleSubmit} className="mt-6 space-y-5">
        <div>
          <label htmlFor="city" className="block text-sm font-medium text-stone-700">
            City
          </label>
          <input
            id="city"
            value={city}
            onChange={(event) => setCity(event.target.value)}
            placeholder="e.g. Boston"
            autoComplete="address-level2"
            className="mt-1 w-full max-w-xs rounded-md border border-stone-300 bg-white px-3 py-2 text-sm focus:border-stone-900 focus:outline-none focus:ring-1 focus:ring-stone-900"
          />
        </div>

        <fieldset>
          <legend className="text-sm font-medium text-stone-700">Occasion</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {OCCASIONS.map((option) => (
              <label
                key={option.value}
                className={`cursor-pointer rounded-full border px-3 py-1.5 text-sm has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-stone-900 ${
                  occasion === option.value
                    ? 'border-stone-900 bg-stone-900 text-white'
                    : 'border-stone-300 bg-white text-stone-700 hover:border-stone-500'
                }`}
              >
                <input
                  type="radio"
                  name="occasion"
                  value={option.value}
                  checked={occasion === option.value}
                  onChange={() => setOccasion(option.value)}
                  className="sr-only"
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>

        <button
          type="submit"
          disabled={loading || !city.trim()}
          className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stone-900 disabled:opacity-60"
        >
          {loading ? 'Building outfits…' : 'Get outfits'}
        </button>
      </form>

      {error && (
        <p role="alert" className="mt-6 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      {result && (
        <div className="mt-10">
          <p className="text-sm text-stone-700">
            {result.weather.city}: {Math.round(result.weather.temp_celsius)}°C, {result.weather.description}
          </p>
          {result.tips && <p className="mt-1 text-sm text-stone-500">{result.tips}</p>}
          {result.source === 'fallback' && (
            <p className="mt-3 text-sm text-stone-500">
              Styling notes are unavailable right now, so these outfits are ranked by score alone.
            </p>
          )}

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {result.outfits.map((outfit, index) => (
              <OutfitCard
                key={outfit.item_ids.join('-')}
                outfit={outfit}
                recommended={index === result.recommended_index}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}