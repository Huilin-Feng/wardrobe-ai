import { useEffect, useState } from 'react'
import { garmentColor, garmentShape } from './garments'

const SKIN = '#E7C7AD'
const SKIN_SHADE = '#E3C1A6'
const HAIR = '#2B2422'

// Neutral base layer shown until the wardrobe has a top, bottom or shoes to wear.
const BASE_TOP = { shape: 'tee', color: '#E4E1DC' }
const BASE_BOTTOM = { shape: 'pants', color: '#B9B4AD' }
const BASE_SHOES = '#202125'

// Body-space outlines in a 200x400 box. Sleeves are drawn for the left arm and mirrored.
const P = {
  torso: 'M68 95Q100 85 132 95L130 208L70 208Z',
  sleeveShort: 'M60 94L82 96L81 132L61 132Z',
  sleeveLong: 'M60 94L82 96L79 207L62 207Z',
  outSleeve: 'M57 92L84 94L81 211L59 211Z',
  panelL: 'M63 93Q80 85 97 89L97 216L63 216Z',
  panelR: 'M137 93Q120 85 103 89L103 216L137 216Z',
  hood: 'M74 99Q68 64 100 66Q132 64 126 99Q114 89 100 91Q86 89 74 99Z',
  pants: 'M72 198L128 198L129 216L121 370L103 370L100 226L97 370L79 370L71 216Z',
  shorts: 'M72 198L128 198L131 262L103 264L100 226L97 264L69 262Z',
  skirt: 'M74 198L126 198L142 288L58 288Z',
}

function Shaded({ d, fill }) {
  return (
    <>
      <path d={d} fill={fill} />
      <path d={d} fill="url(#cl-fig-shade)" />
    </>
  )
}

function look(item, fallback) {
  return item ? { shape: garmentShape(item), color: garmentColor(item) } : fallback
}

function prefersReducedMotion() {
  return window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
}

export default function Figure({ outfit, spinKey, label }) {
  // The clothes change a moment after the twirl starts, while the figure is edge-on.
  const [shown, setShown] = useState(outfit)
  useEffect(() => {
    const timer = setTimeout(() => setShown(outfit), prefersReducedMotion() ? 0 : 190)
    return () => clearTimeout(timer)
  }, [outfit])

  const top = look(shown.top, BASE_TOP)
  const bottom = look(shown.bottom, BASE_BOTTOM)
  const outer = shown.outerwear ? look(shown.outerwear) : null
  const shoes = shown.shoes ? garmentColor(shown.shoes) : BASE_SHOES

  const sleeves = (
    <>
      <Shaded d={top.shape === 'tee' ? P.sleeveShort : P.sleeveLong} fill={top.color} />
      {outer && <Shaded d={P.outSleeve} fill={outer.color} />}
    </>
  )
  const arm = (
    <>
      <path d="M64 98L78 98L77 206L65 206Z" fill={SKIN} />
      {sleeves}
      <circle cx="71" cy="213" r="7" fill={SKIN} />
    </>
  )

  return (
    // Changing the key remounts the wrapper, which replays the twirl animation.
    <div key={spinKey} className={`cl-figure${spinKey ? ' is-twirling' : ''}`}>
      <svg viewBox="0 0 200 400" role="img" aria-label={label}>
        <defs>
          <linearGradient id="cl-fig-shade" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0" stopColor="#000" stopOpacity=".22" />
            <stop offset=".3" stopColor="#000" stopOpacity="0" />
            <stop offset=".72" stopColor="#000" stopOpacity="0" />
            <stop offset="1" stopColor="#000" stopOpacity=".22" />
          </linearGradient>
        </defs>
        <ellipse cx="100" cy="380" rx="46" ry="7" fill="rgba(0,0,0,.18)" />

        <g className="cl-body">
          <path d="M78 200L98 200L96 366L84 366Z" fill={SKIN} />
          <path d="M102 200L122 200L116 366L104 366Z" fill={SKIN} />
          <path d="M78 362L97 362L98 378L71 378Q71 367 78 362Z" fill={shoes} />
          <path d="M122 362L103 362L102 378L129 378Q129 367 122 362Z" fill={shoes} />
          <path d="M71 376H98M102 376H129" stroke="#F1F1EE" strokeWidth="2.4" />

          <g>
            <Shaded d={P[bottom.shape]} fill={bottom.color} />
            {bottom.shape === 'skirt' ? (
              <path d="M88 202L82 288M100 202V288M112 202L118 288" stroke="rgba(0,0,0,.18)" strokeWidth="1.2" />
            ) : (
              <path d="M72 198H128V206H72Z" fill="rgba(0,0,0,.12)" />
            )}
          </g>

          <g className="cl-torso">
            <path d="M70 96Q100 88 130 96L127 202L73 202Z" fill={SKIN} />
            <rect x="92" y="72" width="16" height="24" rx="6" fill={SKIN_SHADE} />
            <Shaded d={P.torso} fill={top.color} />
            <path d="M70 204H130" stroke="rgba(0,0,0,.12)" strokeWidth="2" />
            <path d="M89 90Q100 106 111 90Q100 94 89 90Z" fill={SKIN_SHADE} />
            {outer && (
              <g>
                <Shaded d={P.panelL} fill={outer.color} />
                <Shaded d={P.panelR} fill={outer.color} />
                {outer.shape === 'hoodie' ? (
                  <>
                    <path d={P.hood} fill={outer.color} />
                    <path d={P.hood} fill="rgba(0,0,0,.16)" />
                    <path d="M95 92L94 122M105 92L106 122" stroke="#EDEDEA" strokeWidth="1.4" strokeLinecap="round" />
                  </>
                ) : (
                  <path d="M84 87L97 90L92 105Z M116 87L103 90L108 105Z" fill="rgba(0,0,0,.2)" />
                )}
              </g>
            )}
          </g>

          <g className="cl-arm-l">{arm}</g>
          <g className="cl-arm-r">
            <g transform="matrix(-1 0 0 1 200 0)">{arm}</g>
          </g>

          <g className="cl-head">
            <path d="M73 54Q73 21 100 21Q127 21 127 54L129 86L113 80L87 80L71 86Z" fill={HAIR} />
            <ellipse cx="100" cy="54" rx="22" ry="26" fill="#E9CBB2" />
            <path d="M77 47Q81 25 100 25Q121 25 123 47Q109 37 97 39Q86 40 77 47Z" fill={HAIR} />
            <ellipse className="cl-eye" cx="92" cy="58" rx="2.1" ry="2.7" fill={HAIR} />
            <ellipse className="cl-eye" cx="108" cy="58" rx="2.1" ry="2.7" fill={HAIR} />
            <ellipse cx="87" cy="66" rx="4" ry="2.4" fill="#E99A8C" opacity=".45" />
            <ellipse cx="113" cy="66" rx="4" ry="2.4" fill="#E99A8C" opacity=".45" />
            <path d="M96 69Q100 72 104 69" fill="none" stroke="#9A5B4E" strokeWidth="1.6" strokeLinecap="round" />
          </g>
        </g>
      </svg>
    </div>
  )
}
