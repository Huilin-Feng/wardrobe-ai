// Maps clothing items from the API onto the simple garment shapes the closet can draw.
// The backend stays the source of truth; nothing here is stored.

const NAMED_COLORS = {
  'light blue': '#A8CAEB',
  black: '#2B2B2E',
  white: '#F4F4F1',
  cream: '#EFE8D8',
  grey: '#8A9096',
  gray: '#8A9096',
  navy: '#2F3D5C',
  blue: '#5B7FB8',
  green: '#5E8C5A',
  olive: '#767B56',
  beige: '#D8C8A8',
  khaki: '#B8A97E',
  brown: '#7A5A44',
  red: '#B23A3A',
  burgundy: '#7A2A33',
  pink: '#F0A3C0',
  purple: '#7D5BA6',
  yellow: '#E8CF4A',
  orange: '#E0833A',
}
// Longest names first so "light blue" wins over "blue".
const COLOR_KEYS = Object.keys(NAMED_COLORS).sort((a, b) => b.length - a.length)
const FALLBACK_COLOR = '#9AA0A6'

export function garmentColor(item) {
  const hex = item.hex_color?.trim()
  if (hex && /^#?[0-9a-f]{6}$/i.test(hex)) return hex.startsWith('#') ? hex : `#${hex}`
  const name = (item.color || '').toLowerCase()
  const key = COLOR_KEYS.find((k) => name.includes(k))
  return key ? NAMED_COLORS[key] : FALLBACK_COLOR
}

function searchText(item) {
  return `${item.description || ''} ${item.style || ''}`.toLowerCase()
}

// Returns one of: tee, longsleeve, hoodie, jacket, pants, shorts, skirt, shoe
export function garmentShape(item) {
  const text = searchText(item)
  switch (item.category) {
    case 'top':
      if (/t-?shirt|\btee\b|tank|short[- ]sleeve/.test(text)) return 'tee'
      if (/long[- ]?sleeve|sweater|knit|cardigan|turtleneck|sweatshirt|shirt|blouse/.test(text)) return 'longsleeve'
      return (item.warmth_level ?? 1) >= 3 ? 'longsleeve' : 'tee'
    case 'bottom':
      if (/skirt/.test(text)) return 'skirt'
      if (/shorts/.test(text)) return 'shorts'
      return 'pants'
    case 'outerwear':
      return /hood/.test(text) ? 'hoodie' : 'jacket'
    case 'shoes':
      return 'shoe'
    default:
      return 'tee'
  }
}

const SHAPE_LABELS = {
  tee: 'tee',
  longsleeve: 'long sleeve',
  hoodie: 'hoodie',
  jacket: 'jacket',
  pants: 'pants',
  shorts: 'shorts',
  skirt: 'skirt',
  shoe: 'shoes',
}

// Short label for the rack tag, e.g. "Navy jacket".
export function shortName(item) {
  const shape = garmentShape(item)
  let label = SHAPE_LABELS[shape]
  const text = searchText(item)
  if (shape === 'jacket' && /coat/.test(text)) label = 'coat'
  if (shape === 'pants' && /jean|denim/.test(text)) label = 'jeans'
  if (shape === 'shoe' && /boot/.test(text)) label = 'boots'
  if (shape === 'shoe' && /sneaker/.test(text)) label = 'sneakers'
  const color = (item.color || '').trim()
  if (!color || color === 'unknown') return label.charAt(0).toUpperCase() + label.slice(1)
  return `${color.charAt(0).toUpperCase()}${color.slice(1)} ${label}`
}
