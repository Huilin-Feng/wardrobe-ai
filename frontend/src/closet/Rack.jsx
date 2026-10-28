import { useEffect, useRef } from 'react'
import { garmentColor, garmentShape, shortName } from './garments'

// Front-view outlines in a 120x180 box. CSS turns them sideways on the rack.
const PATHS = {
  tee: 'M32 32L48 26Q60 36 72 26L88 32L110 54L97 67L88 58L88 156L32 156L32 58L23 67L10 54Z',
  longsleeve: 'M32 32L48 26Q60 36 72 26L88 32L104 60L112 148L99 150L89 76L88 156L32 156L31 76L21 150L8 148L16 60Z',
  hood: 'M42 31Q44 6 60 6Q76 6 78 31Q60 41 42 31Z',
  pants: 'M30 26L90 26L95 168L67 168L60 64L53 168L25 168Z',
  shorts: 'M28 26L92 26L98 108L64 110L60 66L56 110L22 108Z',
  skirt: 'M38 26L82 26L104 132L16 132Z',
  shoe: 'M6 32L6 22Q6 14 16 14L34 14Q40 22 54 24L70 27Q77 29 75 34L6 34Z',
}
const NECKLINE = 'M48 26Q60 36 72 26'
const BOTTOM_SHAPES = new Set(['pants', 'shorts', 'skirt'])

function Shaded({ d, fill }) {
  return (
    <>
      <path d={d} fill={fill} />
      <path d={d} fill="url(#cl-shade)" />
    </>
  )
}

function ShirtHanger() {
  return (
    <>
      <path d="M60 22V13a6 6 0 1 1 6-6" fill="none" stroke="#5D6369" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M60 22L20 36M60 22L100 36" stroke="#4A4F55" strokeWidth="3" strokeLinecap="round" />
    </>
  )
}

function ClipHanger() {
  return (
    <>
      <path d="M60 20V13a6 6 0 1 1 6-6" fill="none" stroke="#5D6369" strokeWidth="2.2" strokeLinecap="round" />
      <path d="M26 21H94" stroke="#4A4F55" strokeWidth="3" strokeLinecap="round" />
      <rect x="32" y="19" width="6" height="11" rx="1" fill="#3E4348" />
      <rect x="82" y="19" width="6" height="11" rx="1" fill="#3E4348" />
    </>
  )
}

export function GarmentSVG({ shape, color }) {
  const zip = <path d="M60 36V156" stroke="rgba(0,0,0,.35)" strokeWidth="1.4" />
  return (
    <svg viewBox="0 0 120 180" aria-hidden="true" focusable="false">
      {BOTTOM_SHAPES.has(shape) ? <ClipHanger /> : <ShirtHanger />}

      {shape === 'tee' && (
        <>
          <Shaded d={PATHS.tee} fill={color} />
          <path d={NECKLINE} fill="none" stroke="rgba(0,0,0,.25)" strokeWidth="1.5" />
        </>
      )}
      {shape === 'longsleeve' && (
        <>
          <Shaded d={PATHS.longsleeve} fill={color} />
          <path d={NECKLINE} fill="none" stroke="rgba(0,0,0,.25)" strokeWidth="1.5" />
        </>
      )}
      {shape === 'hoodie' && (
        <>
          <path d={PATHS.hood} fill={color} />
          <path d={PATHS.hood} fill="rgba(0,0,0,.18)" />
          <Shaded d={PATHS.longsleeve} fill={color} />
          {zip}
          <path d="M42 116H78L74 140H46Z" fill="rgba(0,0,0,.1)" />
        </>
      )}
      {shape === 'jacket' && (
        <>
          <Shaded d={PATHS.longsleeve} fill={color} />
          {zip}
          <path d="M46 26L60 40L50 47Z M74 26L60 40L70 47Z" fill="rgba(0,0,0,.2)" />
        </>
      )}
      {(shape === 'pants' || shape === 'shorts') && (
        <>
          <Shaded d={PATHS[shape]} fill={color} />
          <path d="M28 26H92V34H28Z" fill="rgba(0,0,0,.12)" />
        </>
      )}
      {shape === 'skirt' && (
        <>
          <Shaded d={PATHS.skirt} fill={color} />
          <path d="M50 30L44 132M60 30V132M70 30L76 132" stroke="rgba(0,0,0,.18)" strokeWidth="1.2" />
        </>
      )}
    </svg>
  )
}

// One shared gradient that gives every garment a little depth at the edges.
function SharedDefs() {
  return (
    <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden="true" focusable="false">
      <defs>
        <linearGradient id="cl-shade" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor="#000" stopOpacity=".24" />
          <stop offset=".3" stopColor="#000" stopOpacity="0" />
          <stop offset=".72" stopColor="#000" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity=".24" />
        </linearGradient>
      </defs>
    </svg>
  )
}

function RackSlot({ item, worn, hidden, onPick, pushDirection }) {
  const swingRef = useRef(null)
  const name = shortName(item)

  // Restart the swing animation so it plays again on every pass of the pointer.
  function swing() {
    const el = swingRef.current
    if (!el) return
    el.style.setProperty('--dir', pushDirection())
    el.classList.remove('is-swinging')
    void el.offsetWidth
    el.classList.add('is-swinging')
  }

  return (
    <button
      type="button"
      className={`cl-slot${worn ? ' is-worn' : ''}${hidden ? ' is-out' : ''}`}
      aria-pressed={worn}
      aria-label={name}
      aria-hidden={hidden || undefined}
      tabIndex={hidden ? -1 : 0}
      onPointerEnter={(e) => {
        if (e.pointerType === 'mouse') swing()
      }}
      onClick={() => {
        swing()
        onPick(item)
      }}
    >
      <span ref={swingRef} className="cl-swing">
        <span className="cl-turn">
          <GarmentSVG shape={garmentShape(item)} color={garmentColor(item)} />
        </span>
      </span>
      <span className="cl-tag">{name}</span>
    </button>
  )
}

export default function Rack({ items, wornIds, filter, onPick }) {
  const rackRef = useRef(null)
  const lastDX = useRef(1)

  // A garment pushed to the right swings its hem right, which is a counter-clockwise turn.
  const pushDirection = () => (lastDX.current > 0 ? -1 : 1)

  useEffect(() => {
    const rack = rackRef.current
    if (rack) rack.scrollLeft = (rack.scrollWidth - rack.clientWidth) / 2
  }, [items.length])

  return (
    <div className="cl-rack" ref={rackRef}>
      <div
        className="cl-track"
        onPointerMove={(e) => {
          if (e.movementX) lastDX.current = e.movementX
        }}
      >
        <span className="cl-rail" aria-hidden="true" />
        {items.map((item) => (
          <RackSlot
            key={item.id}
            item={item}
            worn={wornIds.has(item.id)}
            hidden={filter !== 'all' && item.category !== filter}
            onPick={onPick}
            pushDirection={pushDirection}
          />
        ))}
      </div>
      <SharedDefs />
    </div>
  )
}

export function ShoeShelf({ shoes, wornId, onPick }) {
  if (shoes.length === 0) return null
  return (
    <div className="cl-shelf" role="group" aria-label="Shoes">
      {shoes.map((item) => {
        const name = shortName(item)
        const worn = item.id === wornId
        return (
          <button
            key={item.id}
            type="button"
            className={`cl-shoe${worn ? ' is-worn' : ''}`}
            aria-pressed={worn}
            aria-label={name}
            onClick={() => onPick(item)}
          >
            <svg viewBox="0 0 80 40" aria-hidden="true" focusable="false">
              <path d={PATHS.shoe} fill={garmentColor(item)} />
              <path d="M6 32H75" stroke="#F1F1EE" strokeWidth="3" />
            </svg>
            <span className="cl-shoe-name">{name}</span>
          </button>
        )
      })}
    </div>
  )
}
