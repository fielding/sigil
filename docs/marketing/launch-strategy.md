# Sigil — Launch Channel Strategy

## Launch Thesis

Sigil's audience is engineering leads, architects, and platform engineers who already care about design docs and architectural governance. They hang out in specific places online. We go to them with a concrete demo, not a landing page.

The launch is optimized for **one viral moment on Hacker News** supported by sustained presence on dev Twitter/X and Reddit. Everything else is amplification.

## Pre-Launch (1-2 weeks before)

### Prep work
- [ ] Polish README (use README-draft.md as base)
- [ ] Record a 90-second terminal demo: `sigil init` -> write a spec -> open PR -> see intent diff comment
- [ ] Create a demo repo (or clean up this repo) that strangers can clone and run in < 2 minutes
- [ ] Write the HN Show post draft
- [ ] Write the launch Twitter thread draft
- [ ] Seed 2-3 real intent docs in the demo repo so the graph viewer has something interesting to show
- [ ] Test the entire flow on a clean machine: clone, init, new, lint, index, viewer, CI

### Build anticipation (optional, low effort)
- Post 1-2 "building in public" tweets showing the graph viewer or a PR comment screenshot
- No teaser campaign. Dev tools don't need hype. They need a working demo.

## Launch Day

### Channel 1: Hacker News (Show HN) — PRIMARY

**Why:** HN is where engineering leads discover tools. A well-positioned Show HN can drive thousands of GitHub stars and genuine adoption. Sigil's thesis ("review intent, not just diffs") is the kind of opinionated take that generates HN discussion.

**Format:** Show HN post

**Title options (pick one):**
- "Show HN: Sigil -- turn specs and ADRs into a reviewable knowledge graph in your Git repo"
- "Show HN: Sigil -- an intent-first engineering CLI that posts architecture diffs on PRs"
- "Show HN: Sigil -- review intent, not just diffs"

**Post body:**
- 3-4 paragraphs: problem, solution, how it works, current state + roadmap
- Link to GitHub repo
- Link to demo repo or live viewer screenshot
- Mention: single Python file, one dependency, MIT license
- End with "I'd love feedback on X" (invite discussion)

**Timing:** Tuesday-Thursday, 9-10am ET. Avoid Mondays and Fridays.

**Engagement plan:** Author monitors and responds to every comment for the first 6 hours. Answer technical questions with specifics. Acknowledge limitations honestly ("gates aren't enforced yet, that's Phase 5"). Don't be defensive about the "just use ADRs" crowd — redirect to what's different (graph, CI, typed edges).

### Channel 2: Twitter/X — AMPLIFICATION

**Why:** Dev Twitter has a strong architecture/DX community. Threads get shared, screenshots get engagement.

**Format:** Launch thread (8-10 tweets)

**Thread structure:**
1. Hook: "Your specs are dead. Here's how to bring them back." + screenshot of PR intent diff
2. Problem: Specs rot in Notion. ADRs are write-only. Architecture is invisible.
3. Solution: Sigil indexes specs, ADRs, and constraints into a knowledge graph in your Git repo.
4. Demo: Terminal recording GIF of `sigil init` -> `sigil new spec` -> graph viewer
5. CI magic: Screenshot of PR comment with intent diff
6. Key features: graph, diff, lint, viewer, bootstrap
7. Philosophy: "Intent should live where code lives"
8. What's next: VS Code extension, gate enforcement, drift detection
9. Link: GitHub repo + "star if this resonates"
10. Invite: "What's your team's biggest pain point with design docs?"

**Supporting posts (day of and day after):**
- Screenshot of the graph viewer with a real graph
- Screenshot of `sigil lint` catching a dangling reference
- "One file. One dependency. That's the whole CLI." + link to sigil.py

**Accounts to tag/mention:** People who tweet about ADRs, architecture governance, platform engineering, developer experience. Don't spam — only mention if genuinely relevant.

### Channel 3: Reddit — AMPLIFICATION

**Subreddits:**
- **r/programming** — "Show r/programming" style post, similar to HN framing
- **r/ExperiencedDevs** — Frame around the problem: "How do you keep architectural decisions alive?"
- **r/softwarearchitecture** — Direct relevance. Post about the intent-first approach.
- **r/devops** / **r/platformengineering** — Frame around CI integration: "We added architecture diffs to our PR comments"

**Format:** Text post with problem-solution structure. Link to repo. Include a screenshot. Don't over-sell.

**Timing:** Post after HN gains traction (if it does). Reddit can amplify an HN front page moment.

### Channel 4: Dev Newsletters and Aggregators — WEEK 1-2

**Submit to:**
- TLDR Newsletter (tldr.tech) — dev tools section
- Changelog News (changelog.com/news)
- Console.dev — curated dev tools newsletter
- Hacker Newsletter — curated HN digest
- DevOps Weekly
- Platform Engineering Weekly

**Format:** Short pitch email. Problem, solution, link, one screenshot.

### Channel 5: Engineering Blogs and Communities — WEEK 2-4

**Write a blog post:** "Why We Built an Intent-First Engineering System"
- Longer form. 1500-2000 words.
- Publish on the repo (docs/blog/) or dev.to / hashnode.
- Cross-post link to HN, Reddit, Twitter.

**Target communities for discussion:**
- ThoughtWorks Technology Radar community
- CNCF Slack (platform engineering channels)
- Locally.dev / DX communities
- Architecture-focused Discord servers

## Post-Launch (Week 2-4)

### Sustain attention
- Respond to every GitHub issue within 24 hours
- Ship one visible improvement per week (badge, new feature, docs fix)
- Write a follow-up post: "What we learned launching Sigil on HN" (if relevant)
- Start a changelog / releases page on GitHub

### Measure what matters
- **GitHub stars** — vanity but signals awareness. Target: 500 in first week from HN.
- **Clones and unique visitors** — GitHub Insights. Real adoption signal.
- **Issues opened** — People trying the tool and hitting edges. Good sign.
- **Forks** — Contributors interested in the project.
- **PR comments posted** — Real CI integration adoption. The north star metric.

### What NOT to do
- Don't buy ads. Dev tools spread by word of mouth and HN/Reddit.
- Don't create a Discord/Slack until there's organic demand (10+ people asking for it).
- Don't launch on Product Hunt. Wrong audience for a CLI tool.
- Don't write a "versus" post comparing to Backstage. Let the positioning doc speak; don't pick fights early.

## Content Calendar (First 4 Weeks)

| Week | Channel | Content |
|---|---|---|
| Pre-launch | Twitter | 1-2 building-in-public posts with screenshots |
| Week 1 (Launch) | HN, Twitter, Reddit | Show HN + launch thread + subreddit posts |
| Week 1 | Newsletters | Submit to 5-6 dev newsletters |
| Week 2 | Blog | "Why We Built an Intent-First Engineering System" |
| Week 2 | Twitter | Technical deep-dive thread on graph diffing |
| Week 3 | Twitter | "How to add intent review to your PRs in 5 minutes" tutorial thread |
| Week 3 | Reddit | Follow-up post in r/ExperiencedDevs with learnings |
| Week 4 | Blog | "Intent Coverage: A New Metric for Architectural Health" |
| Week 4 | Twitter | Showcase thread: real-world graph from a contributor's repo |
