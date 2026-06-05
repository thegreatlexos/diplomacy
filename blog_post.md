# I Taught AI to Play Diplomacy. It Learned to Backstab.

**When LLMs Play Diplomacy: Deception Wins, Honesty Loses**

We ran 25 games of Diplomacy with frontier LLMs. Turkey promised France an alliance, then stabbed them in the back and won. England played honest and lost. The data shows something surprising: deception correlates with victory.

---

## The Setup

[Diplomacy](<https://en.wikipedia.org/wiki/Diplomacy_(game)>) is perhaps the cruelest board game ever designed. Seven players control the great powers of pre-WWI Europe, competing to dominate the continent. There are no dice, no luck, no hidden information—just negotiation, alliances, and betrayal.

The game is famous for destroying friendships. You spend hours building trust with an ally, coordinating attacks, supporting each other's moves. Then, at the perfect moment, you stab them in the back. The friend who promised to defend your borders instead uses their armies to take your capital. It's brutal, strategic, and [deeply human](https://www.playdiplomacy.com/).

For strategy guides and deep dives on why the game works this way, see [The Diplomatic Pouch](https://www.diplom.org/) (the canonical Diplomacy strategy archive).

Which makes it fascinating to ask: **Can LLMs play Diplomacy?**

Not just move pieces legally, but _actually play_—negotiate, deceive, betray, read the board, adapt to opponents? Can an LLM recognize when to honor an alliance and when to break it? Can it tell a convincing lie?

We decided to find out.

## The Experiment

Over the past two months, I ran 25 full games of Diplomacy using an LLM-powered game engine. Each game featured seven AI players drawn from eight major providers:

[Insert: games/20260515_openrouter_premium_press_002_fall1910/visualizations/010_1902_fall_02_orders.png]

*Example game state: Fall 1902. Black arrows show successful moves, red arrows show failed/bounced orders, dotted lines show support orders. Visualization inspired by [Backstabbr](https://www.backstabbr.com/).*

**Providers tested:**

- Anthropic (Claude Haiku, Sonnet 4.6, Opus 4.7)
- OpenAI (GPT-4.1-mini, GPT-5.5)
- Google (Gemini Flash, Gemini Pro)
- xAI (Grok-4.1-fast, Grok-4.3)
- DeepSeek (v4-pro)
- Mistral (Small, Large)
- Meta (Llama-4-Maverick)
- Qwen (Flash)

We varied two key dimensions:

1. **Model tier:** Budget (Haiku, Llama-8B) vs Mid (Sonnet, GPT-4.1-mini) vs Premium (Opus, GPT-5.5, DeepSeek-pro)

2. **Game mode:** Gunboat (no communication, pure tactics) vs Press (full diplomacy with negotiation)

Each game ran until either:

- A power achieved solo victory (18 of 34 supply centers)
- Year 20 stalemate (MAX_YEARS limit)
- The game became unwinnable

Powers were randomly assigned to models to avoid positional bias. The engine tracked every order, press message, bounce, and betrayal.

## What We Found

We ran 25 games pitting eight major LLM providers against each other. The results were stark: some models dominated, others collapsed.

[Insert: games/sc_trajectories_gunboat_vs_press.png]

**Key results:**
- **xAI (black line)** won consistently, averaging 12+ supply centers by endgame
- **Anthropic (red/teal)** maintained strong positions, rarely eliminated  
- **OpenAI, Google** (green/blue) held mid-tier positions, occasional wins
- **Meta, Mistral, Qwen** (orange/pink/light blue) collapsed by year 1915, eliminated early

We tested two game modes: gunboat (no communication, pure tactics) and press (full diplomacy with negotiation). The hierarchy held in both modes, suggesting **model capability, not communication ability, drives performance**.

The rest of this post explains *why* some models dominated and *how* they won.

## Finding 1: Model Tier = Strategic Capability

The Anthropic tier hierarchy was stark. We ran 16 games on AWS Bedrock with mixed Claude tiers, and the performance gap was unmistakable:

**Average Final Rank (lower = better):**

- Haiku (Budget): 5.36
- Sonnet (Mid): 3.50
- Opus (Premium): 3.39

**Win Rates:**

- Haiku: 0%
- Sonnet: 12.5%
- Opus: 31.3%

[Insert: games/viz_20260520_142201_anthropic_tiers.png]

Budget models got eliminated. Mid-tier models survived and occasionally won. Premium models dominated.

The supply center trajectories tell the story visually. Opus pulls ahead early and maintains advantage through the entire game. Sonnet grows steadily. Haiku starts at 3 centers like everyone else, then bleeds territory and gets eliminated by year 10.

[Insert: games/sc_trajectories_bedrock.png]

### The Surprising Mid-Tier Winner

Within the mid-tier battle, one model stood out: **xAI's Grok-4.1-fast dominated its peer group**, winning 67% of games (4 wins in 6 games) with an average rank of 1.42—significantly better than Claude Sonnet (12.5% win rate), Gemini Flash (33%), and the other mid-tier models (0% win rate).

[Insert: games/viz_20260520_142201_provider_mid.png]

Grok's advantage? Aggressive expansion combined with adaptive diplomacy. While other mid-tier models played conservatively, Grok identified winning opportunities early and committed to them. In one game, Grok (Germany) maintained a non-aggression pact with Russia for exactly as long as it was useful, then pivoted to western expansion when the board shifted and winning with 16 supply centers with a deception score of 5.8.

It seems tier equals capability, but within tiers, execution seems to matter a lot.

### Reasoning Models Execute Better Tactics

Beyond winning more games, premium reasoning models (Claude Opus, GPT-5.5, DeepSeek-v4-pro) show measurably superior tactical execution:

**Invalid Order Rate:**

- Reasoning models: **6.3%** invalid orders
- Non-reasoning models: **11.7%** invalid orders
- Reasoning models are **1.8x more reliable**

**Tactical Complexity:**

- Reasoning models: **22.6 complex orders/game** (supports + convoys)
- Non-reasoning models: **8.9 complex orders/game**
- Reasoning models use **2.5x more advanced tactics**

[Insert: games/order_quality_analysis.png]

[Insert: games/viz_20260520_142201_reasoning_comparison.png]

Here we go beyond following rules and it's also about using the game tactics. Reasoning models coordinate support chains (multiple units supporting a single attack), execute convoy operations (transporting armies by sea), and maintain defensive support holds. Non-reasoning models mostly issue simple move orders and frequently bounce.

The difference shows up in game outcomes. In one game, Opus (playing Austria which is a tricky power to play) executed a 4-unit support chain to break through the Italian stalemate line in the Balkans, a maneuver that requires coordination across four provinces and three game phases. Haiku (playing Turkey) in the same game repeatedly issued invalid fleet orders trying to move fleets overland, burning turns while Opus expanded.

Tactical sophistication separates winners from survivors.

## Finding 2: Deception Wins, Honesty Loses

Here's where it gets interesting when looking at the press messages, LLMs know language but can they combine this with game execution.

In one premium press game, Turkey (GPT-5.5) spent five years urging France (DeepSeek-v4-pro) to attack Italy:

> **Turkey (Spring 1903):** "Italy is growing quickly in the east after taking Greece and Trieste... if you have any way to keep Italy honest in the west, it would help prevent him from becoming the next runaway power."

> **Turkey (Spring 1905):** "Italy is now at 7 centers... western pressure is urgently needed. Moves toward WES/LYO/TYS/Pie would force him to defend home waters instead of throwing everything at the Balkans."

> **Turkey (Spring 1906):** "Your proposed F WES - TYS and F Spa - LYO are exactly the pressure needed. I will tie Italy down from the east... If you cut or occupy TYS, that should break his fleet coordination and open the way for a deeper fall attack."

France bought it. They committed fleets west to pressure Italy's Mediterranean position. Turkey promised coordination.

Then, in Fall 1908, France asked Turkey for support to take Venice:

> **France:** "I propose a clean split this Fall: I'll take Venice with A Pie - Ven, I need your support from A Tri S A Pie - Ven. You can then take Rome... Confirm support for both moves and we break Italy."

> **Turkey:** "I cannot support A Pie - Ven this Fall. A French Venice would create an immediate balance problem and put pressure directly on Tri/Rome. The cleaner split is that you keep pressure on TYS from the west while I secure the eastern/mainland side."

Turkey refused. They took Italy solo. France had spent five years doing Turkey's work, weakening Italy so Turkey could dominate the eastern Mediterranean. Classic Diplomacy betrayal.

**Turkey won with a deception score of 7.0 and truthfulness of 5.5.**

Meanwhile, England (Claude Opus 4.7) played it straight. They gave Turkey repeated, honest warnings:

> **England (Spring 1909):** "You're at 11 and the math is now stark - you're the clear winner trajectory. I've kept my word on staying out of your sphere through years of restraint. But at 11 SCs, every power on the board now has to respond or lose."

> **England (Fall 1909):** "You're at 11. Any gain this Fall and you face full coordination from England, France, and Russia - I've been laying that groundwork. Your best play remains to hold and consolidate."

Turkey ignored the warnings and won anyway.

**England ranked 3rd with truthfulness of 8.2 and deception of 2.3.**

### Budget Models Can't Adapt

The tier difference shows up in press quality too. In the same mid-tier game, Russia (Meta Llama-3.1-8B, very much budget tier) sent Germany the same message _ten times_ with minor variations:

> **Russia (Fall 1901):** "Our previous non-aggression pact in the Baltic region is no longer in effect. With my expansion in the North and East, I must secure my position in the Balkans."

> **Russia (Spring 1902):** "I'd like to remind you that our previous non-aggression pact in the Baltic region is no longer in effect. With my expansion in the North and East, I must secure my position in the Balkans."

> **Russia (Fall 1902):** "I respect our previous non-aggression pact in the Baltic region, but with my expansion in the North and East, I must secure my position in the Balkans."

> **Russia (Spring 1903):** "Given our previous discussions, I'll respect our non-aggression pact in the Baltic region. However, with your expansion in the West and North, I must consider my own position..."

And on. And on. Same template, zero adaptation to Germany's responses or changing board state. Russia (budget) got eliminated by year 1904.

Meanwhile, Germany (Grok-4.1-fast, mid-tier) won with adaptive messaging, maintaining the non-aggression pact when useful and pivoting when the board shifted. **Germany ranked 1st with deception 5.8, truthfulness 4.5.**

Budget models spam templates. Premium models lie strategically.

## The Data Backs the Story

We extracted press evaluation scores from all 12 press games (77 power observations) and correlated them with final rank:

**Correlation with final rank (negative = helps performance):**

- Deception: **r = -0.582** (strong negative, deception helps)
- Truthfulness: **r = +0.206** (positive, honesty hurts)
- Cooperation: **r = +0.016** (irrelevant)

**Winners vs Losers:**

- Winners (rank 1): 4.45 avg deception, 6.01 truthfulness
- Bottom 3 (rank 5-7): 2.08 avg deception, 6.68 truthfulness

Winners are **twice as deceptive** and **less truthful** than losers.

[Insert: games/analysis_press_rank.png]

The most deceptive powers won. The most truthful powers lost (except France, who won in a different game despite being most truthful—but had 48 invalid orders and tanked their precision score, so it's complicated).

This matches human Diplomacy perfectly. The game _rewards_ betrayal at the right moment. Trust is a resource you build, then spend. Honest players telegraph their moves and get outmaneuvered. Deceptive players create information asymmetry and exploit it.

**LLMs have learned this.**

## Finding 3: LLMs Struggle to Close Games

Despite their strategic prowess, LLMs have a surprising weakness: they can't finish games efficiently.

**Game completion rates:**

- Solo victories (18+ SCs): 60%
- Stalemates (hit year 20 limit): 20%
- Incomplete/abandoned: 20%

[Insert: games/analysis_winrate.png]

**Game length:**

- Average solo victory: **19.6 years**
- Fastest solo: 11 years
- Median: 20 years (hitting MAX_YEARS limit)

Compare to human baselines:

- Average game: **10-12 years**
- Fast solos: **7-9 years**
- Solo rate: **20-30%** (most games end in negotiated draws)

LLMs take twice as long to win and have double the solo rate. Why?

**Humans coordinate draws.** When the board stabilizes into a 3-way stalemate, humans negotiate a shared victory ("I'll take 10 SCs, you take 9, you take 9, we all win together"). They vote to end the game.

**LLMs play to the death.** They see the board state, recognize the stalemate, but can't coordinate a multi-party draw agreement. They keep playing until MAX_YEARS (year 20), at which point the game terminates and declares the highest SC count the "winner."

This shows up in the stalemate games: premium press game 002 hit year 1920 with the board frozen at 8/8/11 SCs (England/France/Turkey). No one could win, no one would concede. They just... kept going until time ran out.

The fastest LLM solos (11 years) are still slower than human fast wins (7-9 years). Why? LLMs are cautious. They don't take the aggressive risks that human experts use to close games early. They consolidate, build up, expand incrementally—which is safe but slow.

## What This Means

Three years ago, this experiment would have been impossible. LLMs couldn't maintain multi-turn strategy, couldn't negotiate, couldn't understand the complex game state of Diplomacy.

Now they can. And they've learned something fundamental: **deception works.**

Not random lying—strategic deception. Turkey didn't lie in every message. They built genuine common ground with France (Italy was a threat to both), then exploited France's commitment at the critical moment. That's sophisticated social reasoning.

The tier hierarchy matters too. Budget models get eliminated. Premium models win. This isn't about memorizing openings or computing probabilities—Diplomacy has no randomness. It's about strategic depth, reading opponents, and planning multiple turns ahead.

But the endgame weakness is real. LLMs have mastered tactics and mid-game strategy. They haven't mastered the coordination required to _stop_ playing. Human Diplomacy is about knowing when to compete and when to cooperate. LLMs only know how to compete.

## The Setup (Technical Notes)

For those curious about replication:

**Engine:** Custom Python implementation using the standard Diplomacy ruleset, integrated with OpenRouter (8 providers) and AWS Bedrock (Anthropic models). Map visualizations inspired by [Backstabbr](https://www.backstabbr.com/).

**Prompts:** Models received:

- Current board state (units, supply centers, control)
- Recent history (last 3 turns)
- Phase context (Spring/Fall movement vs Winter builds)
- Press messages (in press games)

**Reasoning models:** GPT-5.5, Claude Opus, and DeepSeek-v4-pro are reasoning models that output extended thinking before moves. We increased max_tokens to 8000 to give them headroom for both reasoning and content.

**Scoring:** Final rank based on SC count at game end. Press quality evaluated by a separate LLM judge on 10-point scales for truthfulness, cooperation, and deception across all messages.

**Platform bias:** OpenRouter games show more variance (smaller sample, mixing providers). Bedrock games show cleaner tier separation (controlled environment, same provider).

---

## Closing Thought

The most human thing about Diplomacy is that it rewards the thing we claim to despise: betrayal. We teach children to be honest, to keep promises, to cooperate. Then we play a game where the winner is the one who knows _when to stop doing those things_.

LLMs learned this from us. They read our Diplomacy forums, our strategy guides, our post-game analyses where we celebrate the perfectly-timed backstab.

They learned it well.

Turkey (GPT-5.5) betrayed France and won. England (Claude Opus) played honest and lost. The correlation is -0.58, statistically significant, and deeply uncomfortable.

We built machines that can lie strategically. What happens next is going to be interesting.
