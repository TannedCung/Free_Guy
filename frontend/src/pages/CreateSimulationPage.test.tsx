/**
 * Tests for CreateSimulationPage — map selection + simulation creation flow.
 *
 * Run: npm test  (requires: npm install)
 */

import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

import CreateSimulationPage from './CreateSimulationPage'
import * as mapsApi from '../api/maps'
import * as simsApi from '../api/simulations'

// ── mock react-router navigate ─────────────────────────────────────────────
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router-dom')>()
  return { ...actual, useNavigate: () => mockNavigate }
})

// ── mock Header (avoids unrelated render complexity) ──────────────────────
vi.mock('../components/Header', () => ({ default: () => <header data-testid="header" /> }))

// ── mock API modules ──────────────────────────────────────────────────────
vi.mock('../api/maps')
vi.mock('../api/simulations')

// ── fixtures ──────────────────────────────────────────────────────────────
const MAPS = [
  {
    id: 'the_ville',
    name: 'The Ville',
    description: 'A suburban town.',
    preview_image_url: '',
    max_agents: 25,
  },
  {
    id: 'the_forest',
    name: 'The Forest',
    description: 'A wooded area.',
    preview_image_url: '',
    max_agents: 10,
  },
]

const SIM_RESPONSE = {
  id: 'my-sim',
  name: 'my-sim',
  fork_sim_code: null,
  start_date: null,
  curr_time: null,
  sec_per_step: 10,
  maze_name: 'the_ville',
  persona_names: [],
  step: 0,
  map_id: 'the_ville',
  visibility: 'private',
  owner: 1,
  status: 'pending',
}

function renderPage() {
  return render(
    <MemoryRouter>
      <CreateSimulationPage />
    </MemoryRouter>,
  )
}

// ── tests ─────────────────────────────────────────────────────────────────

describe('CreateSimulationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    ;(mapsApi.fetchMaps as Mock).mockResolvedValue({ maps: MAPS })
    ;(simsApi.createSimulation as Mock).mockResolvedValue(SIM_RESPONSE)
  })

  describe('map loading', () => {
    it('shows a loading indicator while maps are being fetched', () => {
      // fetchMaps never resolves in this test
      ;(mapsApi.fetchMaps as Mock).mockReturnValue(new Promise(() => {}))
      renderPage()
      expect(screen.getByText(/loading maps/i)).toBeInTheDocument()
    })

    it('renders a card for each map returned by the API', async () => {
      renderPage()
      await waitFor(() => expect(screen.getByText('The Ville')).toBeInTheDocument())
      expect(screen.getByText('The Forest')).toBeInTheDocument()
    })

    it('shows map description and max_agents on each card', async () => {
      renderPage()
      await waitFor(() => expect(screen.getByText('A suburban town.')).toBeInTheDocument())
      expect(screen.getByText('A wooded area.')).toBeInTheDocument()
      expect(screen.getByText(/max agents:\s*25/i)).toBeInTheDocument()
      expect(screen.getByText(/max agents:\s*10/i)).toBeInTheDocument()
    })

    it('pre-selects the_ville map by default', async () => {
      renderPage()
      // The_ville card should have the selected style (border-blue-500)
      await waitFor(() => expect(screen.getByText('The Ville')).toBeInTheDocument())
      const villeCard = screen.getByText('The Ville').closest('button')
      expect(villeCard?.className).toMatch(/border-blue-500/)
    })

    it('pre-selects the first map when the_ville is not in the list', async () => {
      const otherMaps = [MAPS[1]] // only "the_forest"
      ;(mapsApi.fetchMaps as Mock).mockResolvedValue({ maps: otherMaps })
      renderPage()
      await waitFor(() => expect(screen.getByText('The Forest')).toBeInTheDocument())
      const forestCard = screen.getByText('The Forest').closest('button')
      expect(forestCard?.className).toMatch(/border-blue-500/)
    })

    it('still renders the form if fetchMaps rejects', async () => {
      ;(mapsApi.fetchMaps as Mock).mockRejectedValue(new Error('Network error'))
      renderPage()
      await waitFor(() => expect(screen.getByRole('button', { name: /create simulation/i })).toBeInTheDocument())
    })
  })

  describe('map selection', () => {
    it('marks a card as selected when clicked', async () => {
      const user = userEvent.setup()
      renderPage()
      await waitFor(() => expect(screen.getByText('The Forest')).toBeInTheDocument())

      await user.click(screen.getByText('The Forest').closest('button')!)
      const forestCard = screen.getByText('The Forest').closest('button')
      expect(forestCard?.className).toMatch(/border-blue-500/)
    })

    it('deselects the previously selected card on new selection', async () => {
      const user = userEvent.setup()
      renderPage()
      await waitFor(() => expect(screen.getByText('The Forest')).toBeInTheDocument())

      await user.click(screen.getByText('The Forest').closest('button')!)
      const villeCard = screen.getByText('The Ville').closest('button')
      // The Ville should no longer have the selected border
      expect(villeCard?.className).not.toMatch(/border-blue-500/)
    })
  })

  describe('form submission', () => {
    it('calls createSimulation with name, selected map, and visibility', async () => {
      const user = userEvent.setup()
      renderPage()
      await waitFor(() => expect(screen.getByText('The Forest')).toBeInTheDocument())

      await user.type(screen.getByPlaceholderText(/e\.g\. my_ville/i), 'my-sim')
      await user.click(screen.getByText('The Forest').closest('button')!)
      await user.click(screen.getByRole('button', { name: /create simulation/i }))

      await waitFor(() =>
        expect(simsApi.createSimulation).toHaveBeenCalledWith('my-sim', undefined, 'the_forest', 'private'),
      )
    })

    it('navigates to the simulation page on success', async () => {
      const user = userEvent.setup()
      renderPage()
      await waitFor(() => expect(screen.getByText('The Ville')).toBeInTheDocument())

      await user.type(screen.getByPlaceholderText(/e\.g\. my_ville/i), 'my-sim')
      await user.click(screen.getByRole('button', { name: /create simulation/i }))

      await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/simulate/my-sim'))
    })

    it('shows an error message when createSimulation rejects', async () => {
      ;(simsApi.createSimulation as Mock).mockRejectedValue(new Error('name already exists'))
      const user = userEvent.setup()
      renderPage()
      await waitFor(() => expect(screen.getByText('The Ville')).toBeInTheDocument())

      await user.type(screen.getByPlaceholderText(/e\.g\. my_ville/i), 'taken-name')
      await user.click(screen.getByRole('button', { name: /create simulation/i }))

      await waitFor(() => expect(screen.getByText(/name already exists/i)).toBeInTheDocument())
    })

    it('disables the submit button while the request is in flight', async () => {
      let resolve!: (v: typeof SIM_RESPONSE) => void
      ;(simsApi.createSimulation as Mock).mockReturnValue(new Promise((r) => (resolve = r)))
      const user = userEvent.setup()
      renderPage()
      await waitFor(() => expect(screen.getByText('The Ville')).toBeInTheDocument())

      await user.type(screen.getByPlaceholderText(/e\.g\. my_ville/i), 'my-sim')
      await user.click(screen.getByRole('button', { name: /create simulation/i }))

      expect(screen.getByRole('button', { name: /creating/i })).toBeDisabled()
      resolve(SIM_RESPONSE)
    })

    it('passes the selected visibility to createSimulation', async () => {
      const user = userEvent.setup()
      renderPage()
      await waitFor(() => expect(screen.getByText('The Ville')).toBeInTheDocument())

      await user.selectOptions(screen.getByRole('combobox'), 'public')
      await user.type(screen.getByPlaceholderText(/e\.g\. my_ville/i), 'my-sim')
      await user.click(screen.getByRole('button', { name: /create simulation/i }))

      await waitFor(() =>
        expect(simsApi.createSimulation).toHaveBeenCalledWith('my-sim', undefined, 'the_ville', 'public'),
      )
    })

    it('Cancel button navigates back to dashboard', async () => {
      const user = userEvent.setup()
      renderPage()
      await waitFor(() => expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument())

      await user.click(screen.getByRole('button', { name: /cancel/i }))
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
    })
  })
})
