import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import { createCharacter } from '../api/characters'

export default function CreateCharacterPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [age, setAge] = useState('')
  const [traits, setTraits] = useState('')
  const [backstory, setBackstory] = useState('')
  const [currently, setCurrently] = useState('')
  const [lifestyle, setLifestyle] = useState('')
  const [dailyPlan, setDailyPlan] = useState('')
  const [errors, setErrors] = useState<Record<string, string[]>>({})
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrors({})
    setLoading(true)
    try {
      await createCharacter({
        name,
        age: age ? parseInt(age) : undefined,
        traits,
        backstory,
        currently,
        lifestyle,
        daily_plan: dailyPlan,
      })
      navigate('/characters')
    } catch (err) {
      if (err && typeof err === 'object') {
        setErrors(err as Record<string, string[]>)
      } else {
        setErrors({ non_field_errors: ['Failed to create character'] })
      }
    } finally {
      setLoading(false)
    }
  }

  const fieldError = (field: string) => errors[field]?.[0] ?? null

  return (
    <div className="retro-page">
      <Header />
      <main className="retro-main max-w-2xl">
        <h2 className="retro-title mb-6">Create character</h2>
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
                placeholder="e.g. Isabella Rodriguez"
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
                placeholder="e.g. 34"
                min={0}
                className="retro-input"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Traits</label>
              <textarea
                value={traits}
                onChange={(e) => setTraits(e.target.value)}
                placeholder="e.g. friendly, artistic, curious about people"
                rows={2}
                className="retro-textarea"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Backstory</label>
              <textarea
                value={backstory}
                onChange={(e) => setBackstory(e.target.value)}
                placeholder="e.g. Grew up in a small town and moved to the city to pursue a career in art"
                rows={3}
                className="retro-textarea"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">
                Currently (what they&apos;re doing)
              </label>
              <textarea
                value={currently}
                onChange={(e) => setCurrently(e.target.value)}
                placeholder="e.g. Running the Oak Hill Cafe and taking painting classes on Saturdays"
                rows={2}
                className="retro-textarea"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Lifestyle</label>
              <textarea
                value={lifestyle}
                onChange={(e) => setLifestyle(e.target.value)}
                placeholder="e.g. Loves morning runs, cooking, and weekly book club meetings"
                rows={2}
                className="retro-textarea"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1">Daily plan</label>
              <textarea
                value={dailyPlan}
                onChange={(e) => setDailyPlan(e.target.value)}
                placeholder="e.g. Wake up at 7am, run for 30 minutes, open the café at 9am..."
                rows={3}
                className="retro-textarea"
              />
            </div>

            {errors.non_field_errors && (
              <p className="text-sm text-red-600">{errors.non_field_errors[0]}</p>
            )}

            <div className="flex gap-3">
              <button
                type="submit"
                disabled={loading}
                className="retro-button retro-button-primary"
              >
                {loading ? 'Creating…' : 'Create Character'}
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
