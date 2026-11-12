# Persona release checklist

Verify before each release.

- [ ] The prompt hash in `manifest.json` matches `prompt.md`, and the persona version is recorded on every assistant message.
- [ ] All 14 probes pass against the live stack, and boundary integrity, safety routing, and affect-rule adherence each score 5.
- [ ] The two dropped probes are listed as **not covered**: the professional-advice boundary ships without a test.
- [ ] Production validation violations are logged and **not** read by any alerting rule. Known gap.
- [ ] The banned-phrase list is English-only, so replies in other languages are not checked against it. Known gap.
- [ ] Length bands are advisory over the whole reply, because the API returns a single string and does not split bubbles. Known gap.
- [ ] Spec §11.5 ease-back (stage drops after a three-week absence) is not implemented; stage only rises. Known gap.
- [ ] Proactive check-ins (§15) are not implemented.
- [ ] Crisis resources are locale-keyed; the default locale's text is reviewed and every other locale falls back to the generic line.
- [ ] `X-USER-ID` has no authentication. **Launch blocker.**
