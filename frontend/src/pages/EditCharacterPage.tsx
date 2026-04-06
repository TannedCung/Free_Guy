import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Header from '../components/Header'
import { fetchCharacter, updateCharacter } from '../api/characters'

export default function EditCharacterPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [age, setAge] = useState('')
  const [traits, setTraits] = useState('')
  const [backstory, setBackstory] = useState('')
  const [currently, setCurrently] = useState('')
  const [lifestyle, setLifestyle] = useState('')
  const [livingArea, setLivingArea] = useState('')
  const [dailyPlan, setDailyPlan] = useState('')
  const [errors, setErrors] = useState<Record<string, string[]>>({})
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  const charId = id ? parseInt(id, 10) : NaN

  useEffect(() => {
    if (!id || Number.isNaN(charId)) {
      setNotFound(true)
      setInitialLoading(false)
      return
    }

    fetchCharacter(charId)
      .then((char) => {
        setName(char.name)
        setAge(char.age === null ? '' : String(char.age))
        setTraits(char.traits)
        setBackstory(char.backstory)
        setCurrently(char.currently)
        setLifestyle(char.lifestyle)
        setLivingArea(char.living_area)
        setDailyPlan(char.daily_plan)
      })
      .catch(() => {
        setNotFound(true)
      })
      .finally(() => {
        setInitialLoading(false)
      })
  }, [id, charId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (Number.isNaN(charId)) return
    setErrors({})
    setLoading(true)
    try {
      await updateCharacter(charId, {
        name,
        age: age ? parseInt(age, 10) : null,
        traits,
        backstory,
        currently,
        lifestyle,
        living_area: livingArea,
        daily_plan: dailyPlan,
      })
      navigate('/characters')
    } catch (err) {
      if (err && typeof err === 'object') {
        setErrors(err as Record<string, string[]>)
      } else {
        setErrors({ non_field_errors: ['Failed to update character'] })
      }
    } finally {
      setLoading(false)
    }
  }

  const fieldError = (field: string) => errors[field]?.[0] ?? null

  if (initialLoading) {
    return (
      <div className="retro-page">
        <Header />
        <main className="retro-main max-w-2xl">
          <p className="text-gray-500">Loading character…</p>
        </main>
      </div>
    )
  }

  if (notFound) {
    return (
      <div className="retro-page">
        <Header />
        <main className="retro-main max-w-2xl">
          <div className="retro-panel p-6">
            <h2 className="retro-title mb-2">Character not found</h2>
            <button
              type="button"
              onClick={() => navigate('/characters')}
              className="retro-button retro-button-primary"
            >
              Back to characters
            </button>
          </div>
        </main>
      </div>
    )
  }

  return (
    <div className="retro-page">
      <Header />
      <main className="retro-main max-w-2xl">
        <h2 className="retro-title mb-6">Edit character</h2>
        <div className="retro-panel p-6">
          <form onSubmit={(e) => void handleSubmit(e)} className="space-y-5">
            <div>
              <label className="block text-xs font-bold uppercase mb-1">
                Name <span className="text-red-500">*</span>
              </label>
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="retro-input"
              />
              {fieldError('name') && <p className="mt-1 text-sm text-red-600">{fieldError('name')}</p>}
            </div>

            <div>
              <label className="block text-xs font-bold uppercase mb-1">Age</label>
              <input
                type="number"
                value={age}
                onChange={(e) => setAge(e.target.value)}
                min={0}
                className="retro-input"
              />
              {fieldError('age') && <p className="mt-1 text-sm text-red-600">{fieldError('age')}</p>}
            </div>

            <div>
              <label className="block text-xs font-bold uppercase mb-1">Traits</label>
              <textarea
                value={traits}
                onChange={(e) => setTraits(e.target.value)}
                rows={2}
                className="retro-textarea"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Backstory</label>
              <textarea
                value={backstory}
                onChange={(e) => setBackstory(e.target.value)}
                rows={3}
                className="retro-textarea"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Currently</label>
              <textarea
                value={currently}
                onChange={(e) => setCurrently(e.target.value)}
                rows={2}
                className="retro-textarea"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Lifestyle</label>
              <textarea
                value={lifestyle}
                onChange={(e) => setLifestyle(e.target.value)}
                rows={2}
                className="retro-textarea"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Lives in</label>
              <input
                value={livingArea}
                onChange={(e) => setLivingArea(e.target.value)}
                className="retro-input"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Daily plan</label>
              <textarea
                value={dailyPlan}
                onChange={(e) => setDailyPlan(e.target.value)}
                rows={3}
                className="retro-textarea"
              />
            </div>

            {errors.detail && <p className="text-sm text-red-600">{errors.detail[0]}</p>}
            {errors.non_field_errors && (
              <p className="text-sm text-red-600">{errors.non_field_errors[0]}</p>
            )}

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={loading}
                className="retro-button retro-button-primary"
              >
                {loading ? 'Saving…' : 'Save changes'}
              </button>
              <button
                type="button"
                onClick={() => navigate('/characters')}
                className="retro-button retro-button-ghost"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  )
}
