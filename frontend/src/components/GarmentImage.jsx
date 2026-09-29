import { useState } from 'react'
import { imageUrl } from '../api/client'

// A square garment photo that falls back to the garment's own color if the photo is missing.
export default function GarmentImage({ item, alt = '', className = '' }) {
  const [imageFailed, setImageFailed] = useState(false)

  return (
    <div
      className={`aspect-square overflow-hidden ${className}`}
      style={{ backgroundColor: item.hex_color }}
    >
      {!imageFailed && (
        <img
          src={imageUrl(item)}
          alt={alt}
          className="h-full w-full object-cover"
          onError={() => setImageFailed(true)}
        />
      )}
    </div>
  )
}