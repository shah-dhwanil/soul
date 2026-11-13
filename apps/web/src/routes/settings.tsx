import { createFileRoute, redirect } from '@tanstack/react-router'
import { useEffect, useRef, useState } from 'react'
import { DialSlider } from '~/components/settings/DialSlider'
import { NameFields } from '~/components/settings/NameFields'
import { PreferenceSelect } from '~/components/settings/PreferenceSelect'
import { Button } from '~/components/ui/button'
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '~/components/ui/dialog'
import {
  isTemperamentDefault,
  mergeSaved,
  patchFromValues,
  rollbackValues,
  settingsAfterReset,
  valuesFromSettings,
  type SettingsValues,
} from '~/lib/settings'
import { sessionGuard } from '~/server/session-guard'
import { fetchSettings, patchSettings, resetLearned } from '~/server/wren'

export const Route = createFileRoute('/settings')({
  beforeLoad: async ({ location }) => {
    const target = await sessionGuard(location.pathname)
    if (target) throw redirect(target)
  },
  loader: async () => {
    const result = await fetchSettings()
    return { settings: result.ok ? result.data : null }
  },
  component: SettingsPage,
})

const DIALS = [
  {
    key: 'warmth' as const,
    label: 'Warmth',
    hint: 'How soft the edges are.',
    min: 5,
    max: 8,
  },
  {
    key: 'directness' as const,
    label: 'Directness',
    hint: 'How plainly I say the thing.',
    min: 4,
    max: 8,
  },
  {
    key: 'humor' as const,
    label: 'Humor',
    hint: 'How often I joke.',
    min: 0,
    max: 6,
  },
  {
    key: 'initiative' as const,
    label: 'Initiative',
    hint: 'How much I bring up on my own.',
    min: 2,
    max: 5,
  },
]

const PREFERENCES = [
  {
    key: 'length' as const,
    label: 'Reply length',
    hint: 'How long a reply tends to be.',
    options: [
      { value: 'brief', label: 'Brief' },
      { value: 'match', label: 'Match me' },
      { value: 'longer', label: 'Longer' },
    ],
  },
  {
    key: 'advice' as const,
    label: 'Advice',
    hint: 'How eagerly I offer my read.',
    options: [
      { value: 'ask_first', label: 'Ask first' },
      { value: 'once', label: 'Once, then never again' },
      { value: 'direct', label: 'Direct' },
    ],
  },
  {
    key: 'checkIns' as const,
    label: 'Check-ins',
    hint: 'Whether I start conversations unprompted.',
    options: [
      { value: 'off', label: 'Off' },
      { value: 'events', label: 'Only around events' },
      { value: 'occasional', label: 'Occasionally' },
    ],
  },
  {
    key: 'emoji' as const,
    label: 'Emoji',
    hint: 'Whether I use them.',
    options: [
      { value: 'never', label: 'Never' },
      { value: 'only_if_i_use_them', label: 'Only if you do' },
    ],
  },
]

function SettingsPage() {
  const { settings } = Route.useLoaderData()
  const [values, setValues] = useState<SettingsValues>(() =>
    valuesFromSettings(settings),
  )
  const [saved, setSaved] = useState<SettingsValues>(() =>
    valuesFromSettings(settings),
  )
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>(
    'idle',
  )
  const [error, setError] = useState<string | null>(null)
  const [learned, setLearned] = useState<Record<string, unknown>>(
    settings?.learned ?? {},
  )
  const [resetting, setResetting] = useState(false)
  const [resetOpen, setResetOpen] = useState(false)

  const savedRef = useRef(saved)
  savedRef.current = saved

  // Save on change: one debounced write, optimistic, rolled back on failure.
  useEffect(() => {
    const patch = patchFromValues(values, saved)
    if (Object.keys(patch).length === 0) return
    const timer = setTimeout(async () => {
      setStatus('saving')
      const result = await patchSettings({ data: patch })
      if (!result.ok) {
        setStatus('error')
        setError('That did not save. Put it back the way it was.')
        // Put back only what this save touched.
        setValues((current) => rollbackValues(current, savedRef.current, patch))
        return
      }
      setStatus('saved')
      // Only what was sent counts as saved.
      setSaved((current) => mergeSaved(current, patch))
      setError(null)
    }, 500)
    return () => clearTimeout(timer)
  }, [values, saved])

  function update<K extends keyof SettingsValues>(
    key: K,
    value: SettingsValues[K],
  ) {
    setValues((current) => ({ ...current, [key]: value }))
  }

  async function onReset() {
    setResetting(true)
    const result = await resetLearned()
    setResetting(false)
    if (!result.ok) {
      setError('That did not reset. Try again.')
      return
    }
    setError(null)
    // The settings are read back after the reset, so what was set by hand
    // is still on screen.
    const state = settingsAfterReset(result.data)
    setLearned(state.learned)
    setValues(state.values)
    setSaved(state.values)
    setResetOpen(false)
  }

  const learnedEntries = Object.entries(learned)

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-12">
      <div className="flex items-baseline justify-between">
        <h1 className="font-display text-3xl">Settings</h1>
        <p aria-live="polite" className="text-sm text-[var(--wren-ink-muted)]">
          {status === 'saving'
            ? 'Saving…'
            : status === 'saved'
              ? 'Saved'
              : status === 'error'
                ? 'Not saved'
                : ''}
        </p>
      </div>

      {error ? (
        <p role="alert" className="mt-4 text-sm text-[#a2442c]">
          {error}
        </p>
      ) : null}

      <section className="mt-10 flex flex-col gap-8">
        <h2 className="font-display text-xl">The dials</h2>
        {DIALS.map((dial) => (
          <DialSlider
            key={dial.key}
            id={`dial-${dial.key}`}
            label={dial.label}
            hint={dial.hint}
            min={dial.min}
            max={dial.max}
            value={values[dial.key]}
            isDefault={isTemperamentDefault(settings, dial.key)}
            onChange={(next) => update(dial.key, next)}
          />
        ))}
      </section>

      <section className="mt-12 flex flex-col gap-8">
        <h2 className="font-display text-xl">How I talk</h2>
        {PREFERENCES.map((preference) => (
          <PreferenceSelect
            key={preference.key}
            id={`preference-${preference.key}`}
            label={preference.label}
            hint={preference.hint}
            value={values[preference.key]}
            options={preference.options}
            onChange={(next) =>
              update(
                preference.key,
                next as SettingsValues[typeof preference.key],
              )
            }
          />
        ))}
      </section>

      <section className="mt-12 flex flex-col gap-6">
        <h2 className="font-display text-xl">What I call you</h2>
        <NameFields
          address={values.address}
          nickname={values.nickname}
          onAddressChange={(next) => update('address', next)}
          onNicknameChange={(next) => update('nickname', next)}
        />
      </section>

      <section className="mt-12 flex flex-col gap-4">
        <h2 className="font-display text-xl">What I have learned</h2>
        {learnedEntries.length === 0 ? (
          <p className="text-sm text-[var(--wren-ink-muted)]">
            Nothing yet. I pick things up as we talk.
          </p>
        ) : (
          <ul className="flex flex-col gap-1 text-sm text-[var(--wren-ink-muted)]">
            {learnedEntries.map(([key, value]) => (
              <li key={key}>
                {key}: {String(value)}
              </li>
            ))}
          </ul>
        )}

        <Dialog open={resetOpen} onOpenChange={setResetOpen}>
          <DialogTrigger asChild>
            <Button variant="outline" className="w-fit rounded-full">
              Reset what I learned
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Reset what I learned?</DialogTitle>
              <DialogDescription>
                Everything I worked out about how you like to talk goes, and
                I start from your temperament again. What you set by hand
                stays.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline" className="rounded-full">
                  Keep it
                </Button>
              </DialogClose>
              <Button
                onClick={onReset}
                disabled={resetting}
                className="rounded-full"
              >
                {resetting ? 'Resetting…' : 'Reset'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </section>
    </div>
  )
}
