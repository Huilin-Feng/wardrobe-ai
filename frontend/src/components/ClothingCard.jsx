import GarmentImage from './GarmentImage'

export default function ClothingCard({ item, onDelete, deleting }) {
  return (
    <article className="overflow-hidden rounded-lg border border-stone-200 bg-white">
      <GarmentImage
        item={item}
        alt={item.description || `${item.color} ${item.category}`}
        className="border-b border-stone-200"
      />

      <div className="space-y-3 p-3">
        <div className="flex items-center gap-2">
          <span
            className="h-3 w-3 shrink-0 rounded-full border border-stone-300"
            style={{ backgroundColor: item.hex_color }}
            aria-hidden="true"
          />
          <p className="truncate text-sm font-medium capitalize text-stone-900">{item.color}</p>
        </div>

        <dl className="grid grid-cols-2 gap-y-1 text-xs">
          <dt className="text-stone-400">Style</dt>
          <dd className="capitalize text-stone-700">{item.style}</dd>
          <dt className="text-stone-400">Warmth</dt>
          <dd className="text-stone-700">{item.warmth_level} / 5</dd>
        </dl>

        <button
          type="button"
          onClick={() => onDelete(item.id)}
          disabled={deleting}
          className="text-xs text-stone-500 underline-offset-2 hover:text-red-700 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-stone-900 disabled:opacity-50"
        >
          {deleting ? 'Removing…' : 'Remove'}
        </button>
      </div>
    </article>
  )
}