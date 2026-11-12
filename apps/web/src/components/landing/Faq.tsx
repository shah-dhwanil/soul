import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '~/components/ui/accordion'

const QUESTIONS = [
  {
    question: 'What is Wren?',
    answer:
      'Wren is an AI that remembers what you choose to share and says what it actually thinks. It has a way of being — a temperament — that you pick once, and it does not change to please you.',
  },
  {
    question: 'Is Wren a therapist, coach, or assistant?',
    answer:
      'No. Wren is a companion. It does not diagnose, prescribe, or manage your life, and it stays out of medical, legal, and financial decisions. If something you are dealing with needs a professional, Wren will say so.',
  },
  {
    question: 'What does Wren remember?',
    answer:
      'What you tell it, and what it notices about how you talk: the jokes you start, the way you push back, what you care about. You can read everything it has noticed on your page, and you can reset what it has learned at any time.',
  },
  {
    question: 'What happens to my conversations?',
    answer:
      'They are stored so Wren can remember them. Your account is an email and a password; there is nothing else to sign up for, and nothing in the product is used for advertising.',
  },
  {
    question: 'Can Wren be wrong?',
    answer:
      'Yes, and it will not pretend otherwise. Wren says what it thinks, once, and it will tell you when it does not know something.',
  },
]

export function Faq() {
  return (
    <section className="mx-auto w-full max-w-3xl px-6 py-20 sm:py-28">
      <h2 className="font-display text-3xl sm:text-4xl">Questions, answered.</h2>
      <Accordion type="single" collapsible className="mt-10">
        {QUESTIONS.map((item, index) => (
          <AccordionItem key={item.question} value={`item-${index}`}>
            <AccordionTrigger className="text-left font-medium">
              {item.question}
            </AccordionTrigger>
            <AccordionContent className="leading-relaxed text-[var(--wren-ink-muted)]">
              {item.answer}
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </section>
  )
}
