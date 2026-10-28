import { useEffect, useMemo, useRef } from 'react'

// Turns the OpenWeatherMap "main" condition (Clear, Clouds, Rain, Snow, Mist...) into a backdrop.
// Night is based on the viewer's local clock, which is close enough for a backdrop.
export function skyState(condition, now = new Date()) {
  const c = (condition || '').toLowerCase()
  const hour = now.getHours()
  if (/rain|drizzle|thunder/.test(c)) return 'rain'
  if (/snow|sleet/.test(c)) return 'snow'
  if (hour >= 19 || hour < 6) return 'night'
  if (c === 'clear') return 'sunny'
  return 'cloudy'
}

const SKIES = ['sunny', 'cloudy', 'rain', 'snow', 'night']
const CLOUD_PATH = 'M20 40Q20 20 40 22Q46 6 64 12Q80 2 92 18Q112 16 112 34Q120 46 104 50L28 50Q14 50 20 40Z'
const CLOUDS = [
  { top: '9%', width: 150, duration: 64, delay: -12 },
  { top: '25%', width: 104, duration: 86, delay: -50 },
  { top: '2%', width: 200, duration: 104, delay: -80 },
]

function useParticles(stageRef, canvasRef, sky) {
  useEffect(() => {
    const stage = stageRef.current
    const canvas = canvasRef.current
    if (!stage || !canvas) return undefined
    const ctx = canvas.getContext('2d')
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    const mode = sky === 'rain' || sky === 'snow' ? sky : null
    let width = 0
    let height = 0
    let parts = []
    let frameId = 0

    function makeParts() {
      const count = mode === 'rain' ? Math.round(width / 3.2) : Math.round(width / 5)
      parts = Array.from({ length: count }, () =>
        mode === 'rain'
          ? { x: Math.random() * width, y: Math.random() * height, len: 10 + Math.random() * 12, speed: 9 + Math.random() * 6 }
          : { x: Math.random() * width, y: Math.random() * height, r: 1.2 + Math.random() * 2.4, speed: 0.6 + Math.random() * 1.1, phase: Math.random() * 6.28 },
      )
    }

    function draw() {
      ctx.clearRect(0, 0, width, height)
      if (mode === 'rain') {
        ctx.strokeStyle = 'rgba(225,233,240,.55)'
        ctx.lineWidth = 1.1
        ctx.beginPath()
        for (const d of parts) {
          ctx.moveTo(d.x, d.y)
          ctx.lineTo(d.x - d.len * 0.22, d.y + d.len)
          if (!reduce) {
            d.y += d.speed
            d.x -= d.speed * 0.22
            if (d.y > height) {
              d.y = -20
              d.x = Math.random() * (width + 60)
            }
          }
        }
        ctx.stroke()
      } else if (mode === 'snow') {
        ctx.fillStyle = 'rgba(255,255,255,.92)'
        for (const f of parts) {
          ctx.beginPath()
          ctx.arc(f.x, f.y, f.r, 0, Math.PI * 2)
          ctx.fill()
          if (!reduce) {
            f.phase += 0.02
            f.y += f.speed
            f.x += Math.sin(f.phase) * 0.5
            if (f.y > height) {
              f.y = -6
              f.x = Math.random() * width
            }
          }
        }
      }
    }

    function loop() {
      draw()
      frameId = requestAnimationFrame(loop)
    }

    function resize() {
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      width = stage.clientWidth
      height = stage.clientHeight
      canvas.width = width * dpr
      canvas.height = height * dpr
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
      if (mode) makeParts()
      if (reduce || !mode) draw()
    }

    const observer = new ResizeObserver(resize)
    observer.observe(stage)
    resize()
    if (mode && !reduce) loop()

    return () => {
      cancelAnimationFrame(frameId)
      observer.disconnect()
    }
  }, [stageRef, canvasRef, sky])
}

export default function WeatherStage({ sky, children }) {
  const stageRef = useRef(null)
  const canvasRef = useRef(null)
  useParticles(stageRef, canvasRef, sky)

  const stars = useMemo(
    () =>
      Array.from({ length: 42 }, () => ({
        left: `${Math.random() * 100}%`,
        top: `${Math.random() * 100}%`,
        size: Math.random() < 0.8 ? 1.5 : 2.5,
        delay: `${-Math.random() * 3}s`,
      })),
    [],
  )

  return (
    <div ref={stageRef} className="cl-stage" data-weather={sky}>
      {SKIES.map((name) => (
        <div key={name} className={`cl-sky cl-sky-${name}`} aria-hidden="true" />
      ))}
      <div className="cl-stars" aria-hidden="true">
        {stars.map((s, i) => (
          <span key={i} style={{ left: s.left, top: s.top, width: s.size, height: s.size, animationDelay: s.delay }} />
        ))}
      </div>
      <div className="cl-sun" aria-hidden="true" />
      <div className="cl-moon" aria-hidden="true" />
      {CLOUDS.map((c, i) => (
        <svg
          key={i}
          className="cl-cloud"
          viewBox="0 0 124 56"
          aria-hidden="true"
          focusable="false"
          style={{ top: c.top, width: c.width, animationDuration: `${c.duration}s`, animationDelay: `${c.delay}s` }}
        >
          <path d={CLOUD_PATH} />
        </svg>
      ))}
      <div className="cl-floor" aria-hidden="true" />
      {children}
      <canvas ref={canvasRef} className="cl-fx" aria-hidden="true" />
    </div>
  )
}
