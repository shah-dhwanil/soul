import { createFileRoute } from '@tanstack/react-router'
import { ClosingCta, Footer } from '~/components/landing/ClosingCta'
import { Faq } from '~/components/landing/Faq'
import { Hero } from '~/components/landing/Hero'
import { TemperamentTeaser } from '~/components/landing/TemperamentTeaser'
import { WhatIs } from '~/components/landing/WhatIs'

export const Route = createFileRoute('/')({
  component: LandingPage,
})

function LandingPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <Hero />
      <WhatIs />
      <TemperamentTeaser />
      <Faq />
      <ClosingCta />
      <Footer />
    </div>
  )
}
