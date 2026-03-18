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
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="max-w-5xl mx-auto px-4 py-10">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-3xl font-bold text-gray-900">My Characters</h2>
          <Link
            to="/characters/new"
            className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            Create character
          </Link>
        </div>

        {deleteError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-600 text-sm">
            {deleteError}
          </div>
        )}

        {loading ? (
          <p className="text-gray-500">Loading…</p>
        ) : characters.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-100 shadow p-8 text-center text-gray-500">
            No characters yet.{' '}
            <Link to="/characters/new" className="text-blue-600 hover:underline">
              Create your first character
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {characters.map((char) => (
              <div key={char.id} className="bg-white rounded-xl border border-gray-100 shadow p-5">
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
                  <Link
                    to={`/characters/${char.id}/edit`}
                    className="text-sm text-blue-600 hover:underline"
                  >
                    Edit
                  </Link>
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
                      className="text-sm text-red-600 hover:underline"
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
