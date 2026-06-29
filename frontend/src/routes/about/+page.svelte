<svelte:head>
  <title>About // DIPLOMACY_AI_LAB</title>
</svelte:head>

<div class="about-page">
  <!-- Header -->
  <header class="header">
    <div class="header-content">
      <div class="logo">
        <a href="/" class="terminal-prompt glow-green">DIPLOMACY_AI_LAB</a>
        <span class="version">v2.0.1</span>
      </div>
      <nav class="nav">
        <a href="/games">GAMES</a>
        <a href="/about" class="active">ABOUT</a>
        <a href="https://example.substack.com" target="_blank" rel="noopener">RESEARCH</a>
        <a href="https://github.com/thegreatlexos/diplomacy" target="_blank" rel="noopener">GITHUB</a>
      </nav>
    </div>
  </header>

  <main class="main">
    <div class="content">
      <h1 class="terminal-prompt glow-cyan">ABOUT_THIS_PROJECT</h1>

      <section class="section">
        <h2 class="section-title terminal-text glow-green">// WHAT_IS_THIS</h2>
        <p>
          DIPLOMACY_AI_LAB is an open research platform analyzing strategic reasoning capabilities
          in frontier Large Language Models through the board game Diplomacy.
        </p>
        <p>
          Unlike deterministic games like chess or Go, Diplomacy requires simultaneous move submission,
          multi-turn planning, coalition building, negotiation, and strategic deception. It tests capabilities
          that are fundamental to real-world multi-agent coordination.
        </p>
      </section>

      <section class="section">
        <h2 class="section-title terminal-text glow-green">// METHODOLOGY</h2>
        <div class="system-panel">
          <div class="system-panel-title">EXPERIMENT_DESIGN</div>
          <ul class="method-list">
            <li><span class="hex-value">0x19</span> (25) complete games across 8 AI providers</li>
            <li>Two game modes: Gunboat (no communication) and Press (full diplomacy)</li>
            <li>Randomized power assignments to control positional bias</li>
            <li>Three model tiers: Budget (Haiku, Llama-8B), Mid (Sonnet, GPT-4.1-mini), Premium (Opus, GPT-5)</li>
            <li>Systematic scoring: Precision (order quality), Performance (SC growth), Press quality (truthfulness/deception)</li>
          </ul>
        </div>

        <div class="system-panel">
          <div class="system-panel-title">TECHNICAL_STACK</div>
          <ul class="method-list">
            <li><strong>Game Engine:</strong> Custom Python implementation, full Diplomacy ruleset</li>
            <li><strong>LLM Routing:</strong> AWS Bedrock + OpenRouter for multi-provider support</li>
            <li><strong>Visualization:</strong> Matplotlib map rendering with order arrows</li>
            <li><strong>Analysis:</strong> NumPy, Pandas, correlation analysis</li>
            <li><strong>Frontend:</strong> SvelteKit + FastAPI backend</li>
          </ul>
        </div>
      </section>

      <section class="section">
        <h2 class="section-title terminal-text glow-green">// KEY_FINDINGS</h2>

        <div class="findings-list">
          <div class="finding system-panel">
            <div class="finding-header">
              <span class="finding-metric hex-value">r = -0.58</span>
              <span class="finding-title">DECEPTION CORRELATES WITH VICTORY</span>
            </div>
            <p>
              Statistical analysis of 12 press games (77 power observations) shows strong negative correlation
              between deception score and final rank. Winners average <span class="hex-value">4.45</span> deception,
              losers average <span class="hex-value">2.08</span> — a 2x difference.
            </p>
            <p>
              Example: GPT-5.5 (Turkey) spent 5 years urging France to attack Italy, then refused support
              when France needed it, taking Italy solo. Deception score: <span class="glow-amber">7.0/10</span>, Result: <span class="glow-green">Won</span>.
            </p>
          </div>

          <div class="finding system-panel">
            <div class="finding-header">
              <span class="finding-metric hex-value">67%</span>
              <span class="finding-title">GROK DOMINATES MID-TIER</span>
            </div>
            <p>
              xAI Grok-4.1-fast achieved 67% win rate in mid-tier matchups (4 wins in 6 games),
              significantly outperforming Claude Sonnet (12.5%), Gemini Flash (33%), and others (0%).
            </p>
            <p>
              Success factors: Aggressive territorial expansion combined with adaptive diplomatic messaging.
              Average rank: <span class="hex-value">1.42</span> (best in tier).
            </p>
          </div>

          <div class="finding system-panel">
            <div class="finding-header">
              <span class="finding-metric hex-value">TIER = CAPABILITY</span>
              <span class="finding-title">CLEAR PERFORMANCE HIERARCHY</span>
            </div>
            <p>
              16 Bedrock games with mixed tiers show unmistakable hierarchy:
            </p>
            <ul class="finding-stats">
              <li>Premium (Opus): <span class="glow-green">31.3%</span> win rate, <span class="hex-value">3.39</span> avg rank</li>
              <li>Mid (Sonnet): <span class="glow-cyan">12.5%</span> win rate, <span class="hex-value">3.50</span> avg rank</li>
              <li>Budget (Haiku): <span class="glow-amber">0%</span> win rate, <span class="hex-value">5.36</span> avg rank (usually eliminated)</li>
            </ul>
          </div>

          <div class="finding system-panel">
            <div class="finding-header">
              <span class="finding-metric hex-value">2x SLOWER</span>
              <span class="finding-title">LLMS STRUGGLE TO CLOSE GAMES</span>
            </div>
            <p>
              Average solo victory: <span class="hex-value">19.6 years</span> vs human baseline of <span class="hex-value">10-12 years</span>.
              Fastest LLM solo: <span class="hex-value">11 years</span> (still slower than human fast wins at 7-9 years).
            </p>
            <p>
              Root cause: LLMs cannot coordinate multi-party draw agreements. They play to MAX_YEARS limit
              even when board is stalemated. 20% of games hit year 20 without a winner.
            </p>
          </div>
        </div>
      </section>

      <section class="section">
        <h2 class="section-title terminal-text glow-green">// READ_MORE</h2>
        <div class="cta-grid">
          <a href="https://example.substack.com/p/llm-diplomacy-deception-wins" target="_blank" rel="noopener" class="cta-card system-panel">
            <div class="cta-title">FULL RESEARCH PAPER</div>
            <p class="cta-description">2,450-word deep dive: Turkey's betrayal, budget model template spam, game completion analysis</p>
            <div class="cta-link terminal-text glow-cyan">> READ_ON_SUBSTACK</div>
          </a>

          <a href="https://github.com/thegreatlexos/diplomacy" target="_blank" rel="noopener" class="cta-card system-panel">
            <div class="cta-title">SOURCE CODE</div>
            <p class="cta-description">Complete game engine, analysis scripts, and dataset. MIT license, contributions welcome.</p>
            <div class="cta-link terminal-text glow-cyan">> VIEW_ON_GITHUB</div>
          </a>

          <a href="/games" class="cta-card system-panel">
            <div class="cta-title">EXPLORE GAMES</div>
            <p class="cta-description">Browse all 25 games with turn-by-turn visualization, orders, press messages, and scoring.</p>
            <div class="cta-link terminal-text glow-cyan">> OPEN_ARCHIVE</div>
          </a>
        </div>
      </section>

      <section class="section">
        <h2 class="section-title terminal-text glow-green">// CONTACT</h2>
        <div class="contact-panel system-panel">
          <p>Built by <a href="https://twitter.com/yourhandle" target="_blank" class="hex-value">@yourhandle</a></p>
          <p>Questions, feedback, or collaboration inquiries: <a href="mailto:your@email.com" class="hex-value">your@email.com</a></p>
          <p class="terminal-text" style="margin-top: 16px; color: var(--text-dim);">
            > OPEN_SOURCE // MIT_LICENSE // 2026
          </p>
        </div>
      </section>
    </div>
  </main>
</div>

<style>
  .about-page {
    min-height: 100vh;
    background: var(--bg-primary);
  }

  /* Header - same as other pages */
  .header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    z-index: 1000;
    backdrop-filter: blur(10px);
  }

  .header-content {
    max-width: 1400px;
    margin: 0 auto;
    padding: 16px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 18px;
    font-weight: 700;
  }

  .logo a {
    text-decoration: none;
  }

  .version {
    color: var(--text-dim);
    font-size: 12px;
  }

  .nav {
    display: flex;
    gap: 32px;
  }

  .nav a {
    font-size: 13px;
    font-weight: 500;
    transition: all 0.2s;
  }

  .nav a.active {
    color: var(--accent-green);
  }

  /* Main content */
  .main {
    padding: 100px 24px 60px;
    max-width: 1000px;
    margin: 0 auto;
  }

  .content h1 {
    font-size: 48px;
    font-weight: 700;
    margin-bottom: 60px;
  }

  .section {
    margin-bottom: 60px;
  }

  .section-title {
    font-size: 24px;
    font-weight: 700;
    margin-bottom: 24px;
  }

  .section p {
    color: var(--text-secondary);
    line-height: 1.8;
    margin-bottom: 16px;
  }

  .method-list {
    list-style: none;
    padding: 0;
  }

  .method-list li {
    color: var(--text-secondary);
    padding: 8px 0;
    border-bottom: 1px solid var(--border-color);
  }

  .method-list li:last-child {
    border-bottom: none;
  }

  /* Findings */
  .findings-list {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .finding {
    padding: 24px;
  }

  .finding-header {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;
  }

  .finding-metric {
    font-size: 24px;
    font-weight: 700;
  }

  .finding-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--accent-green);
    text-transform: uppercase;
  }

  .finding p {
    margin-bottom: 12px;
  }

  .finding-stats {
    list-style: none;
    padding-left: 0;
    margin-top: 12px;
  }

  .finding-stats li {
    padding: 6px 0;
    color: var(--text-secondary);
  }

  /* CTAs */
  .cta-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
  }

  .cta-card {
    display: block;
    padding: 24px;
    transition: all 0.3s;
  }

  .cta-card:hover {
    transform: translateY(-4px);
  }

  .cta-title {
    font-size: 16px;
    font-weight: 700;
    color: var(--accent-amber);
    margin-bottom: 12px;
    text-transform: uppercase;
  }

  .cta-description {
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.6;
    margin-bottom: 16px;
    min-height: 60px;
  }

  .cta-link {
    padding-top: 16px;
    border-top: 1px solid var(--border-color);
  }

  /* Contact */
  .contact-panel {
    padding: 24px;
  }

  .contact-panel p {
    margin-bottom: 8px;
  }

  @media (max-width: 768px) {
    .cta-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
