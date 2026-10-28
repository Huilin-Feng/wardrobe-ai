import { useEffect, useMemo, useState } from 'react'
import { describeError, getWeather, imageUrl, listClothing, recommendOutfit } from '../api/client'
import Figure from '../closet/Figure'
import Rack, { ShoeShelf } from '../closet/Rack'
import WeatherStage, { skyState } from '../closet/WeatherStage'
import { garmentColor, garmentShape, shortName } from '../closet/garments'
import '../closet/closet.css'

const FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'top', label: 'Tops' },
  { id: 'bottom', label: 'Bottoms' },
  { id: 'outerwear', label: 'Outerwear' },
]
const HANGING = new Set(['top', 'bottom', 'outerwear'])
const EMPTY_OUTFIT = { top: null, bottom: null, outerwear: null, shoes: null }
const CITY_KEY = 'closet-city'

function readSavedCity() {
  try {
    return localStorage.getItem(CITY_KEY) || 'San Jose'
  } catch {
    return 'San Jose'
  }
}

function firstIdOf(items, category) {
  return items.find((i) => i.category === category)?.id ?? null
}

// Quick on-screen advice. The real ranking still comes from the scoring engine.
function outfitHint(weather, outfit) {
  if (!weather) return ''
  const temp = weather.temp_celsius
  const wet = /rain|drizzle|thunder|snow/i.test(weather.condition || '')
  if (wet && !outfit.outerwear) return 'Wet weather today. Add outerwear from the rack.'
  if (temp < 8 && outfit.bottom && garmentShape(outfit.bottom) !== 'pants') return 'Too cold for bare legs. Try long pants.'
  if (temp < 12 && !outfit.outerwear) return `${Math.round(temp)}°C out. A jacket or hoodie would help.`
  if (temp >= 26 && outfit.outerwear) return `${Math.round(temp)}°C out. You could leave the outer layer.`
  if (!outfit.shoes) return 'Pick a pair of shoes to finish the outfit.'
  return 'This works for today.'
}

function FocusCard({ item }) {
  const [failed, setFailed] = useState(false)
  return (
    <div className="cl-card cl-overlay">
      {failed ? (
        <span className="cl-card-swatch" style={{ background: garmentColor(item) }} />
      ) : (
        <img src={imageUrl(item.image_url)} alt="" onError={() => setFailed(true)} />
      )}
      <div>
        <p className="cl-card-name">{shortName(item)}</p>
        <p className="cl-card-meta">Warmth {item.warmth_level}/5</p>
      </div>
    </div>
  )
}

export default function ClosetPage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [worn, setWorn] = useState(EMPTY_OUTFIT)
  const [focusId, setFocusId] = useState(null)
  const [spinKey, setSpinKey] = useState(0)
  const [filter, setFilter] = useState('all')
  const [cityInput, setCityInput] = useState(readSavedCity)
  const [city, setCity] = useState(cityInput)
  const [weather, setWeather] = useState(null)
  const [weatherError, setWeatherError] = useState(null)
  const [dressing, setDressing] = useState(false)

  useEffect(() => {
    listClothing()
      .then((data) => {
        setItems(data)
        setWorn({
          top: firstIdOf(data, 'top'),
          bottom: firstIdOf(data, 'bottom'),
          outerwear: null,
          shoes: firstIdOf(data, 'shoes'),
        })
      })
      .catch((err) => setError(describeError(err)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    let cancelled = false
    setWeatherError(null)
    getWeather(city)
      .then((data) => {
        if (!cancelled) setWeather(data)
      })
      .catch((err) => {
        if (cancelled) return
        setWeather(null)
        setWeatherError(describeError(err))
      })
    return () => {
      cancelled = true
    }
  }, [city])

  const byId = useMemo(() => new Map(items.map((i) => [i.id, i])), [items])
  const outfit = useMemo(
    () => ({
      top: byId.get(worn.top) ?? null,
      bottom: byId.get(worn.bottom) ?? null,
      outerwear: byId.get(worn.outerwear) ?? null,
      shoes: byId.get(worn.shoes) ?? null,
    }),
    [byId, worn],
  )
  const wornIds = useMemo(() => new Set(Object.values(worn).filter((id) => id != null)), [worn])

  const hanging = items.filter((i) => HANGING.has(i.category))
  const shoes = items.filter((i) => i.category === 'shoes')
  const visibleCount = filter === 'all' ? hanging.length : hanging.filter((i) => i.category === filter).length
  const sky = weather ? skyState(weather.condition) : 'cloudy'
  const focused = focusId != null ? byId.get(focusId) : null
  const wornNames = [outfit.outerwear, outfit.top, outfit.bottom, outfit.shoes].filter(Boolean).map(shortName)
  const figureLabel = wornNames.length ? `Figure wearing ${wornNames.join(', ')}` : 'Figure in a plain base outfit'

  function pick(item) {
    setWorn((current) => {
      if (item.category === 'outerwear') {
        return { ...current, outerwear: current.outerwear === item.id ? null : item.id }
      }
      return { ...current, [item.category]: item.id }
    })
    setFocusId(item.id)
    setSpinKey((k) => k + 1)
  }

  function submitCity(event) {
    event.preventDefault()
    const next = cityInput.trim()
    if (!next) return
    try {
      localStorage.setItem(CITY_KEY, next)
    } catch {
      // Private browsing can block storage; the city still applies for this visit.
    }
    setCity(next)
  }

  // Reuses the existing recommendation endpoint and dresses the figure in the top pick.
  async function dressForToday() {
    setDressing(true)
    setError(null)
    try {
      const result = await recommendOutfit(city, 'casual')
      const best = result.outfits?.[result.recommended_index ?? 0]
      if (!best) throw new Error('No outfit came back for today.')
      const next = { ...EMPTY_OUTFIT }
      for (const id of best.item_ids) {
        const item = byId.get(id)
        if (item && item.category in next) next[item.category] = id
      }
      setWorn((current) => ({
        top: next.top ?? current.top,
        bottom: next.bottom ?? current.bottom,
        outerwear: next.outerwear,
        shoes: next.shoes ?? current.shoes,
      }))
      setFocusId(null)
      setSpinKey((k) => k + 1)
    } catch (err) {
      setError(describeError(err))
    } finally {
      setDressing(false)
    }
  }

  if (loading) return <p className="text-sm text-stone-500">Loading your closet…</p>

  return (
    <section className="cl-page">
      <div className="cl-wall">
        <div className="cl-head">
          <div>
            <h2 className="cl-title">Closet</h2>
            <p className="cl-count">
              {visibleCount} {visibleCount === 1 ? 'piece' : 'pieces'} on the rack
            </p>
          </div>
          <form className="cl-city" onSubmit={submitCity}>
            <label htmlFor="cl-city-input" className="sr-only">
              City
            </label>
            <input
              id="cl-city-input"
              value={cityInput}
              onChange={(e) => setCityInput(e.target.value)}
              placeholder="City"
              autoComplete="address-level2"
            />
            <button type="submit">Update weather</button>
          </form>
        </div>

        {hanging.length === 0 ? (
          <p className="cl-empty">Your rack is empty. Add clothes on the Wardrobe tab and they’ll hang here.</p>
        ) : (
          <>
            <Rack items={hanging} wornIds={wornIds} filter={filter} onPick={pick} />
            <nav className="cl-filters" aria-label="Filter clothes">
              {FILTERS.map((f) => (
                <button key={f.id} type="button" aria-pressed={filter === f.id} onClick={() => setFilter(f.id)}>
                  {f.label}
                </button>
              ))}
            </nav>
          </>
        )}
        <ShoeShelf shoes={shoes} wornId={worn.shoes} onPick={pick} />
      </div>

      <WeatherStage sky={sky}>
        <Figure outfit={outfit} spinKey={spinKey} label={figureLabel} />

        <div className="cl-chip cl-overlay">
          {weather ? (
            <>
              <p className="cl-chip-main">
                {weather.condition}, {Math.round(weather.temp_celsius)}°C
              </p>
              <p className="cl-chip-sub">{weather.city}</p>
              <p className="cl-chip-hint">{outfitHint(weather, outfit)}</p>
            </>
          ) : (
            <p className="cl-chip-hint">{weatherError ?? 'Checking the weather…'}</p>
          )}
        </div>

        {focused && <FocusCard key={focused.id} item={focused} />}

        {error && (
          <p className="cl-error cl-overlay" role="alert">
            {error}
          </p>
        )}
        <button type="button" className="cl-dress cl-overlay" onClick={dressForToday} disabled={dressing || !weather}>
          {dressing ? 'Picking an outfit…' : 'Dress me for today'}
        </button>
        <p className="sr-only" aria-live="polite">
          {wornNames.length ? `Wearing ${wornNames.join(', ')}` : ''}
        </p>
      </WeatherStage>
    </section>
  )
}
