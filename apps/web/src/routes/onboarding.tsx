import {
  createFileRoute,
  redirect,
  useNavigate,
  useRouter,
} from '@tanstack/react-router'
import { useMutation } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { BeatProgress } from '~/components/onboarding/BeatProgress'
import { MeetFrame } from '~/components/onboarding/MeetFrame'
import { OpeningReveal } from '~/components/onboarding/OpeningReveal'
import { StepAccount } from '~/components/onboarding/StepAccount'
import { StepDials } from '~/components/onboarding/StepDials'
import { StepName } from '~/components/onboarding/StepName'
import { TemperamentDuel } from '~/components/onboarding/TemperamentDuel'
import { dialsFrom, startingBeat, type BeatKey } from '~/lib/onboarding'
import type { AuthUser, Dials, Settings, UserSummary } from '~/lib/types'
import { completeOnboarding, login, me, register } from '~/server/auth'
import { sessionGuard } from '~/server/session-guard'
import {
  changeTemperament,
  createUser,
  fetchSettings,
  fetchUserSummary,
  patchSettings,
  temperaments,
} from '~/server/wren'

export const Route = createFileRoute('/onboarding')({
  beforeLoad: async ({ location }) => {
    const target = await sessionGuard(location.pathname)
    if (target) throw redirect(target)
  },
  loader: async () => {
    const [meResult, temperamentsResult] = await Promise.all([
      me(),
      temperaments(),
    ])
    const user = meResult.ok ? meResult.data : null
    const seeds = temperamentsResult.ok ? temperamentsResult.data : []

    let summary: UserSummary | null = null
    let settings: Settings | null = null
    if (user && user.onboardingStep >= 1) {
      const [summaryResult, settingsResult] = await Promise.all([
        fetchUserSummary(),
        fetchSettings(),
      ])
      summary = summaryResult.ok ? summaryResult.data : null
      settings = settingsResult.ok ? settingsResult.data : null
    }

    return { user, seeds, summary, settings }
  },
  component: OnboardingPage,
})

function OnboardingPage() {
  const { user: initialUser, seeds, summary, settings } = Route.useLoaderData()
  const navigate = useNavigate()
  const router = useRouter()

  const [user, setUser] = useState<AuthUser | null>(initialUser)
  const [beat, setBeat] = useState<BeatKey>(() => startingBeat(initialUser))
  const [completed, setCompleted] = useState<BeatKey[]>([])
  const [winnerId, setWinnerId] = useState<string | null>(
    summary?.temperament ?? null,
  )
  const [changingTemperament, setChangingTemperament] = useState(false)
  const [settingsState, setSettingsState] = useState<Settings | null>(settings)
  const [error, setError] = useState<string | null>(null)

  const registerMutation = useMutation({
    mutationFn: (input: { email: string; password: string }) =>
      register({ data: input }),
    onSuccess: (result) => {
      if (!result.ok) {
        setError(
          result.code === 'email_exists'
            ? 'That email is already registered. Try signing in instead.'
            : 'That did not work. Try again in a moment.',
        )
        return
      }
      setError(null)
      setUser(result.data)
      setCompleted((current) => [...current, 'account'])
      setBeat('meet')
    },
  })

  const temperamentMutation = useMutation({
    mutationFn: (input: { temperamentId: string; change: boolean }) =>
      input.change
        ? changeTemperament({ data: { temperamentId: input.temperamentId } })
        : createUser({ data: { temperamentId: input.temperamentId } }),
    onSuccess: (result) => {
      if (!result.ok) {
        setError('The choice did not save. Try again.')
        return
      }
      setError(null)
      setWinnerId(result.data.temperament)
      setCompleted((current) => [...current, 'duel'])
      setBeat('name')
    },
  })

  const nameMutation = useMutation({
    mutationFn: (address: string) => patchSettings({ data: { address } }),
    onSuccess: (result) => {
      if (!result.ok) {
        setError('That name did not save. Try again.')
        return
      }
      setError(null)
      setSettingsState(result.data)
      setCompleted((current) => [...current, 'name'])
      setBeat('dials')
    },
  })

  const dialsMutation = useMutation({
    mutationFn: (dials: Dials) =>
      patchSettings({
        data: {
          warmth: dials.warmth,
          directness: dials.directness,
          humor: dials.humor,
          initiative: dials.initiative,
        },
      }),
    onSuccess: (result) => {
      if (!result.ok) {
        setError('Those dials did not save. Try again.')
        return
      }
      setError(null)
      setSettingsState(result.data)
      setCompleted((current) => [...current, 'dials'])
      setBeat('reveal')
    },
  })

  const completeMutation = useMutation({
    mutationFn: () => completeOnboarding(),
    onSuccess: async (result) => {
      if (!result.ok) {
        setError('Something went wrong on the way in. Try again.')
        return
      }
      await navigate({ href: '/chat' })
      // The header reads the session: re-run the root loader.
      await router.invalidate()
    },
  })

  const winner = useMemo(
    () => seeds.find((seed) => seed.id === winnerId) ?? null,
    [seeds, winnerId],
  )

  const initialName =
    typeof settingsState?.explicit?.address === 'string'
      ? settingsState.explicit.address
      : ''

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-14">
      <div className="mb-10">
        <BeatProgress current={beat} completed={completed} />
      </div>

      {beat === 'account' ? (
        <StepAccount
          user={user}
          pending={registerMutation.isPending}
          error={error}
          onRegister={(email, password) =>
            registerMutation.mutate({ email, password })
          }
          onContinue={() => {
            setCompleted((current) => [...current, 'account'])
            setBeat('meet')
          }}
        />
      ) : null}

      {beat === 'meet' ? (
        <MeetFrame
          onContinue={() => {
            setCompleted((current) => [...current, 'meet'])
            setBeat('duel')
          }}
        />
      ) : null}

      {beat === 'duel' ? (
        <div className="flex flex-col gap-6">
          {changingTemperament ? (
            <button
              type="button"
              className="self-start text-sm text-[var(--wren-ink-muted)] underline underline-offset-4"
              onClick={() => {
                setChangingTemperament(false)
                setBeat(summary && summary.temperament ? 'name' : 'meet')
              }}
            >
              Keep {summary?.temperament ?? 'this one'}
            </button>
          ) : null}
          <TemperamentDuel
            temperaments={seeds}
            pending={temperamentMutation.isPending}
            error={error}
            onComplete={(id) =>
              temperamentMutation.mutate({
                temperamentId: id,
                change: Boolean(user && user.onboardingStep >= 1),
              })
            }
          />
        </div>
      ) : null}

      {beat === 'name' ? (
        <div className="flex flex-col gap-6">
          {user && user.onboardingStep >= 1 ? (
            <button
              type="button"
              className="self-start text-sm text-[var(--wren-ink-muted)] underline underline-offset-4"
              onClick={() => {
                setChangingTemperament(true)
                setBeat('duel')
              }}
            >
              Pick again
            </button>
          ) : null}
          <StepName
            initialName={initialName}
            pending={nameMutation.isPending}
            error={error}
            onSubmit={(address) => nameMutation.mutate(address)}
          />
        </div>
      ) : null}

      {beat === 'dials' ? (
        <StepDials
          initialDials={dialsFrom(settingsState)}
          sampleLine={winner?.sampleReply ?? 'What’s on your plate?'}
          pending={dialsMutation.isPending}
          error={error}
          onSubmit={(dials) => dialsMutation.mutate(dials)}
        />
      ) : null}

      {beat === 'reveal' ? (
        <OpeningReveal
          firstLine={winner?.firstLine ?? 'Hi. I’m Wren.'}
          pending={completeMutation.isPending}
          error={error}
          onContinue={() => completeMutation.mutate()}
        />
      ) : null}
    </div>
  )
}
