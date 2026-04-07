import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Header from '../components/Header'
import { fetchCharacters, deleteCharacter, type Character } from '../api/characters'

export default function CharactersPage() {
  const [characters, setCharacters] = useState<Character[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const load = async () => {
    try {
      const res = await fetchCharacters()
      setCharacters(res.characters)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const handleDelete = async (char: Character) => {
    if (char.status === 'in_simulation') return
    setDeleteError(null)
    try {
      await deleteCharacter(char.id)
      await load()
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : 'Failed to delete')
    }
  }

  return (
    <div className="retro-page">
      <Header />
      <main className="retro-main">
        <div className="flex items-center justify-between mb-6">
          <h2 className="retro-title">My Characters</h2>
          <Link
            to="/characters/new"
            className="retro-button retro-button-primary"
          >
            Create character
          </Link>
        </div>

        {deleteError && (
          <div className="retro-panel mb-4 p-3 text-sm text-red-600">
            {deleteError}
          </div>
        )}

        {loading ? (
          <p className="text-gray-500">Loading…</p>
        ) : characters.length === 0 ? (
          <div className="retro-panel retro-empty-state p-8">
            No characters yet.{' '}
            <Link to="/characters/new" className="retro-link">
              Create your first character
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {characters.map((char) => (
              <div key={char.id} className="retro-panel p-5">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-semibold text-gray-900">{char.name}</h3>
                    {char.age !== null && (
                      <p className="text-sm text-gray-500">Age: {char.age}</p>
                    )}
                    <p className="text-sm text-gray-500 mt-1">
                      Status:{' '}
                      <span
                        className={
                          char.status === 'in_simulation'
                            ? 'text-green-600 font-medium'
                            : 'text-gray-600'
                        }
                      >
                        {char.status === 'in_simulation' ? 'In simulation' : 'Available'}
                      </span>
                    </p>
                  </div>
                </div>
                <div className="flex gap-2 mt-3">
                  {char.status === 'in_simulation' ? (
                    <span
                      className="text-sm text-gray-400 cursor-not-allowed"
                      title="Character is in a simulation and cannot be edited"
                    >
                      Edit
                    </span>
                  ) : (
                    <Link
                      to={`/characters/${char.id}/edit`}
                      className="text-sm retro-link"
                    >
                      Edit
                    </Link>
                  )}
                  {char.status === 'in_simulation' ? (
                    <span
                      className="text-sm text-gray-400 cursor-not-allowed"
                      title="Character is in a simulation"
                    >
                      Delete
                    </span>
                  ) : (
                    <button
                      onClick={() => void handleDelete(char)}
                      className="text-sm text-red-600 underline"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
