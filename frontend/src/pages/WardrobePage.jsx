import { useEffect, useRef, useState } from 'react'
import ClothingCard from '../components/ClothingCard'
import { deleteClothing, describeError, listClothing, uploadClothing } from '../api/client'

const CATEGORY_ORDER = ['top', 'bottom', 'outerwear', 'shoes', 'accessory']
const CATEGORY_LABELS = {
  top: 'Tops',
  bottom: 'Bottoms',
  outerwear: 'Outerwear',
  shoes: 'Shoes',
  accessory: 'Accessories',
  other: 'Unsorted',
}

function groupByCategory(items) {
  const groups = CATEGORY_ORDER
    .map((category) => ({ category, items: items.filter((i) => i.category === category) }))
    .filter((group) => group.items.length > 0)

  const known = new Set(CATEGORY_ORDER)
  const other = items.filter((i) => !known.has(i.category))
  if (other.length > 0) groups.push({ category: 'other', items: other })

  return groups
}

export default function WardrobePage() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [error, setError] = useState(null)
  const fileInput = useRef(null)

  useEffect(() => {
    listClothing()
      .then(setItems)
      .catch((err) => setError(describeError(err)))
      .finally(() => setLoading(false))
  }, [])

  async function handleFileChosen(event) {
    const file = event.target.files?.[0]
    event.target.value = '' // lets the same file be chosen again later
    if (!file) return

    setUploading(true)
    setError(null)
    try {
      const created = await uploadClothing(file)
      setItems((current) => [created, ...current])
    } catch (err) {
      setError(describeError(err))
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Remove this item from your wardrobe?')) return

    setDeletingId(id)
    setError(null)
    try {
      await deleteClothing(id)
      setItems((current) => current.filter((item) => item.id !== id))
    } catch (err) {
      setError(describeError(err))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-stone-900">Your wardrobe</h2>
          <p className="mt-1 text-sm text-stone-500">
            {items.length} {items.length === 1 ? 'item' : 'items'}
          </p>
        </div>

        <input
          ref={fileInput}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={handleFileChosen}
        />
        <button
          type="button"
          onClick={() => fileInput.current?.click()}
          disabled={uploading}
          className="rounded-md bg-stone-900 px-4 py-2 text-sm font-medium text-white hover:bg-stone-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-stone-900 disabled:opacity-60"
        >
          {uploading ? 'Analyzing photo…' : 'Add a photo'}
        </button>
      </div>

      {error && (
        <p role="alert" className="mt-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      {loading ? (
        <p className="mt-8 text-sm text-stone-500">Loading your wardrobe…</p>
      ) : items.length === 0 ? (
        <div className="mt-8 rounded-lg border border-dashed border-stone-300 p-8 text-center">
          <p className="text-sm text-stone-700">Your wardrobe is empty.</p>
          <p className="mt-1 text-sm text-stone-500">
            Add a photo of a top, a pair of bottoms and some shoes to get your first outfit.
          </p>
        </div>
      ) : (
        groupByCategory(items).map((group) => (
          <div key={group.category} className="mt-8">
            <h3 className="text-sm font-medium text-stone-700">
              {CATEGORY_LABELS[group.category]}{' '}
              <span className="text-stone-400">{group.items.length}</span>
            </h3>
            <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
              {group.items.map((item) => (
                <ClothingCard
                  key={item.id}
                  item={item}
                  onDelete={handleDelete}
                  deleting={deletingId === item.id}
                />
              ))}
            </div>
          </div>
        ))
      )}
    </section>
  )
}