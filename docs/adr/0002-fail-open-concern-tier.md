# Fail-open concern tier

When the Clef decision call fails, the concern tier resolves to `normal` and the turn directive says so explicitly. We chose fail-open because a Cloudflare outage that makes every user get asked whether they are thinking about suicide is worse than a missed tier; the cost is that a Clef outage also disarms the prompt's inline concern check. Revisit if the Clef failure rate or concern-tier precision make this untenable.
