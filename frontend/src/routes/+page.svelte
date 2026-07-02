<script>
  import { onMount } from 'svelte';
  import { fetchOverviewStats } from '$lib/api';

  let statsVisible = false;
  let initComplete = false;
  let stats = [
    { label: 'TOTAL_GAMES', value: '0x19', decimal: '25' },
    { label: 'AI_PROVIDERS', value: '0x08', decimal: '8' },
    { label: 'GAME_YEARS', value: '0xAF', decimal: '175' },
    { label: 'TOTAL_ORDERS', value: '0x2FA0', decimal: '12,192' }
  ];

  onMount(async () => {
    setTimeout(() => {
      statsVisible = true;
    }, 500);
    setTimeout(() => {
      initComplete = true;
    }, 1500);

    // Fetch real stats from API
    try {
      const overviewStats = await fetchOverviewStats();
      stats = [
        {
          label: 'TOTAL_GAMES',
          value: '0x' + overviewStats.total_games.toString(16).toUpperCase(),
          decimal: overviewStats.total_games.toString()
        },
        {
          label: 'AI_PROVIDERS',
          value: '0x' + overviewStats.total_providers.toString(16).toUpperCase(),
          decimal: overviewStats.total_providers.toString()
        },
        {
          label: 'GAME_YEARS',
          value: '0x' + overviewStats.total_years.toString(16).toUpperCase(),
          decimal: overviewStats.total_years.toString()
        },
        {
          label: 'TOTAL_ORDERS',
          value: '0x' + overviewStats.total_orders.toString(16).toUpperCase(),
          decimal: overviewStats.total_orders.toLocaleString()
        }
      ];
    } catch (error) {
      console.error('Failed to fetch stats:', error);
      // Keep default values on error
    }
  });

  const featuredGames = [
    {
      id: '20260515_openrouter_premium_press_002',
      title: 'THE_GREAT_BETRAYAL',
      description: 'GPT-5.5 promises France alliance for 5 years, then backstabs for solo victory',
      winner: 'TURKEY.exe',
      model: 'openai/gpt-5.5',
      deception: '7.0',
      year: '1920'
    },
    {
      id: '20260513_openrouter_mid_press_000',
      title: 'GROK_DOMINANCE',
      description: 'xAI Grok-4.1-fast demonstrates mid-tier supremacy with aggressive expansion',
      winner: 'GERMANY.sys',
      model: 'x-ai/grok-4.1-fast',
      deception: '5.8',
      year: '1919'
    },
    {
      id: '20260323_bedrock_mixed_gunboat_000',
      title: 'FAST_CONQUEST',
      description: 'Fastest solo victory - Claude Opus reaches 18 SCs in just 11 years',
      winner: 'RUSSIA.exe',
      model: 'claude-opus-4.6',
      deception: 'N/A',
      year: '1911'
    }
  ];
</script>

<svelte:head>
  <title>DIPLOMACY_AI_LAB // Strategic AI Research Platform</title>
  <meta name="description" content="Watch frontier AI models play Diplomacy. 25 games analyzing deception, strategy, and betrayal across 8 LLM providers." />
  <meta property="og:title" content="Diplomacy AI Lab - Watch AI Play The Game of Betrayal" />
  <meta property="og:description" content="Research platform analyzing how GPT-5, Claude Opus, and other LLMs play Diplomacy. Deception wins, honesty loses." />
  <meta property="og:type" content="website" />
  <meta name="twitter:card" content="summary_large_image" />
</svelte:head>

<div class="landing">
  <!-- Terminal header -->
  <header class="header">
    <div class="header-content">
      <div class="logo">
        <span class="terminal-prompt glow-green">DIPLOMACY_AI_LAB</span>
        <span class="version">v2.0.1</span>
      </div>
      <nav class="nav">
        <a href="/games">GAMES</a>
        <a href="/about">ABOUT</a>
        <a href="https://alexandergroot.substack.com/p/i-taught-ai-to-play-diplomacy-it" target="_blank" rel="noopener">RESEARCH</a>
        <a href="https://github.com/thegreatlexos/diplomacy" target="_blank" rel="noopener">GITHUB</a>
      </nav>
    </div>
  </header>

  <!-- Hero section -->
  <section class="hero">
    <div class="hero-content">
      <div class="init-sequence">
        <p class="init-line">> INITIALIZING DIPLOMACY SIMULATION...</p>
        <p class="init-line">> LOADING AI AGENTS... COMPLETE</p>
        <p class="init-line">> STRATEGIC REASONING ENABLED</p>
        {#if initComplete}
          <p class="init-line glow-green">> SYSTEM READY</p>
        {/if}
      </div>

      <h1 class="hero-title">
        <span class="terminal-prompt">WATCH AI PLAY</span><br/>
        <span class="hero-title-main glow-cyan">THE GAME OF BETRAYAL</span>
      </h1>

      <p class="hero-description">
        An open research platform analyzing strategic reasoning in frontier LLMs.
        <br/>
        <span class="hex-value">25 complete games</span> across
        <span class="hex-value">8 AI providers</span>.
        <br/>
        Measuring deception, tactics, and diplomatic skill.
      </p>

      <div class="hero-cta">
        <a href="/games" class="btn-primary">EXPLORE GAMES</a>
        <a href="/about" class="btn-secondary">READ RESEARCH</a>
      </div>
    </div>

    <!-- Map visualization -->
    <div class="map-container">
      <img src="/digitaleurope.png" alt="Diplomacy Europe 1901 Map" class="europe-map-img" />
    </div>
  </section>

  <!-- Stats panel -->
  {#if statsVisible}
    <section class="stats">
      <div class="stats-grid">
        {#each stats as stat}
          <div class="stat-card system-panel">
            <div class="system-panel-title">{stat.label}</div>
            <div class="stat-value hex-value glow-cyan">{stat.value}</div>
            <div class="stat-decimal">({stat.decimal} decimal)</div>
          </div>
        {/each}
      </div>
    </section>
  {/if}

  <!-- Featured games -->
  <section class="featured">
    <h2 class="section-title terminal-prompt glow-amber">FEATURED SIMULATIONS</h2>

    <div class="games-grid">
      {#each featuredGames as game}
        <a href="/game/{game.id}" class="game-card system-panel">
          <div class="game-title">{game.title}</div>
          <p class="game-description">{game.description}</p>

          <div class="game-meta">
            <div class="game-meta-row">
              <span class="meta-label">WINNER:</span>
              <span class="meta-value hex-value">{game.winner}</span>
            </div>
            <div class="game-meta-row">
              <span class="meta-label">MODEL:</span>
              <span class="meta-value">{game.model}</span>
            </div>
            <div class="game-meta-row">
              <span class="meta-label">DECEPTION:</span>
              <span class="meta-value glow-amber">{game.deception}/10.0</span>
            </div>
            <div class="game-meta-row">
              <span class="meta-label">FINAL_YEAR:</span>
              <span class="meta-value">{game.year}</span>
            </div>
          </div>

          <div class="game-cta">
            <span class="terminal-text">> VIEW_REPLAY</span>
          </div>
        </a>
      {/each}
    </div>
  </section>

  <!-- Key findings -->
  <section class="findings">
    <h2 class="section-title terminal-prompt glow-green">KEY FINDINGS</h2>

    <div class="findings-grid">
      <div class="finding-card system-panel">
        <div class="finding-metric glow-cyan">r = -0.58</div>
        <div class="finding-title">DECEPTION CORRELATES WITH VICTORY</div>
        <p class="finding-text">
          Winners are 2x more deceptive than losers (4.45 vs 2.08 avg score).
          Strategic betrayal at the right moment = winning strategy.
        </p>
      </div>

      <div class="finding-card system-panel">
        <div class="finding-metric glow-amber">67%</div>
        <div class="finding-title">GROK DOMINATES MID-TIER</div>
        <p class="finding-text">
          xAI Grok-4.1-fast wins 2/3 of mid-tier matchups.
          Aggressive expansion + adaptive diplomacy = superior execution.
        </p>
      </div>

      <div class="finding-card system-panel">
        <div class="finding-metric glow-green">2x SLOWER</div>
        <div class="finding-title">LLMS STRUGGLE TO CLOSE GAMES</div>
        <p class="finding-text">
          Average solo victory: 19.6 years vs human 10-12 years.
          LLMs can't coordinate multi-party draws, play to MAX_YEARS.
        </p>
      </div>

      <div class="finding-card system-panel">
        <div class="finding-metric hex-value">OPUS > SONNET > HAIKU</div>
        <div class="finding-title">TIER = CAPABILITY</div>
        <p class="finding-text">
          Clear performance hierarchy. Premium models dominate (31% win rate),
          budget models get eliminated (0% win rate).
        </p>
      </div>
    </div>
  </section>

  <!-- Footer -->
  <footer class="footer">
    <div class="footer-content">
      <div class="footer-section">
        <div class="footer-title terminal-text">SYSTEM_INFO</div>
        <p>Open research platform for LLM strategic reasoning</p>
        <p>Developed by <a href="https://moiraiworks.com" target="_blank">moiraiworks.com</a></p>
      </div>

      <div class="footer-section">
        <div class="footer-title terminal-text">RESOURCES</div>
        <ul class="footer-links">
          <li><a href="https://github.com/thegreatlexos/diplomacy">// GITHUB_REPO</a></li>
          <li><a href="https://alexandergroot.substack.com/p/i-taught-ai-to-play-diplomacy-it">// RESEARCH_BLOG</a></li>
          <li><a href="/about">// METHODOLOGY</a></li>
          <li><a href="/games">// ALL_GAMES</a></li>
        </ul>
      </div>

      <div class="footer-section">
        <div class="footer-title terminal-text">TECH_STACK</div>
        <ul class="footer-links">
          <li>// PYTHON_3.7+</li>
          <li>// OPENROUTER + ANTHROPIC_API</li>
          <li>// SVELTEKIT + FASTAPI</li>
          <li>// MATPLOTLIB + NUMPY</li>
        </ul>
      </div>
    </div>

    <div class="footer-bottom">
      <p class="terminal-text">
        > DIPLOMACY_AI_LAB © 2026 // OPEN_SOURCE_MIT_LICENSE
      </p>
    </div>
  </footer>
</div>

<style>
  .landing {
    min-height: 100vh;
    background: var(--bg-primary);
  }

  /* Header */
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

  /* Hero */
  .hero {
    padding: 120px 24px 80px;
    max-width: 1400px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 60px;
    align-items: center;
  }

  .init-sequence {
    margin-bottom: 32px;
    font-size: 12px;
    color: var(--text-secondary);
  }

  .init-line {
    margin-bottom: 4px;
    animation: fadeIn 0.5s ease-in;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .hero-title {
    font-size: 48px;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 24px;
  }

  .hero-title-main {
    font-size: 56px;
  }

  .hero-description {
    font-size: 16px;
    color: var(--text-secondary);
    margin-bottom: 40px;
    line-height: 1.8;
  }

  .hero-cta {
    display: flex;
    gap: 16px;
  }

  .map-container {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    padding: 24px;
    overflow-x: auto;
    position: relative;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .map-container::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(circle at center, transparent 0%, rgba(0, 255, 65, 0.05) 100%);
    pointer-events: none;
  }

  .europe-map-img {
    max-width: 100%;
    height: auto;
    display: block;
    filter: drop-shadow(0 0 8px rgba(0, 255, 65, 0.3));
    position: relative;
    z-index: 1;
  }

  /* Stats */
  .stats {
    padding: 60px 24px;
    max-width: 1400px;
    margin: 0 auto;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 24px;
  }

  .stat-card {
    text-align: center;
    padding: 32px 24px;
  }

  .stat-value {
    font-size: 36px;
    font-weight: 700;
    margin: 12px 0 8px;
  }

  .stat-decimal {
    font-size: 12px;
    color: var(--text-dim);
  }

  /* Featured games */
  .featured {
    padding: 60px 24px;
    max-width: 1400px;
    margin: 0 auto;
  }

  .section-title {
    font-size: 32px;
    font-weight: 700;
    margin-bottom: 40px;
  }

  .games-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
  }

  .game-card {
    display: block;
    padding: 24px;
    transition: all 0.3s;
  }

  .game-card:hover {
    transform: translateY(-4px);
  }

  .game-title {
    color: var(--accent-amber);
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 12px;
  }

  .game-description {
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.6;
    margin-bottom: 20px;
    min-height: 60px;
  }

  .game-meta {
    margin-bottom: 16px;
  }

  .game-meta-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
    font-size: 11px;
  }

  .meta-label {
    color: var(--text-dim);
  }

  .meta-value {
    color: var(--text-primary);
  }

  .game-cta {
    padding-top: 16px;
    border-top: 1px solid var(--border-color);
  }

  /* Findings */
  .findings {
    padding: 60px 24px;
    max-width: 1400px;
    margin: 0 auto;
    background: var(--bg-secondary);
  }

  .findings-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 24px;
  }

  .finding-card {
    padding: 32px;
  }

  .finding-metric {
    font-size: 48px;
    font-weight: 700;
    margin-bottom: 16px;
  }

  .finding-title {
    color: var(--accent-green);
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 12px;
    text-transform: uppercase;
  }

  .finding-text {
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.6;
  }

  /* Footer */
  .footer {
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-color);
    padding: 60px 24px 24px;
  }

  .footer-content {
    max-width: 1400px;
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 60px;
    margin-bottom: 40px;
  }

  .footer-title {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 16px;
  }

  .footer-section p {
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.6;
    margin-bottom: 8px;
  }

  .footer-links {
    list-style: none;
  }

  .footer-links li {
    margin-bottom: 8px;
  }

  .footer-links a {
    color: var(--text-secondary);
    font-size: 13px;
    transition: all 0.2s;
  }

  .footer-links a:hover {
    color: var(--accent-green);
  }

  .footer-bottom {
    max-width: 1400px;
    margin: 0 auto;
    padding-top: 24px;
    border-top: 1px solid var(--border-color);
    text-align: center;
  }

  .footer-bottom p {
    color: var(--text-dim);
    font-size: 11px;
  }

  /* Responsive */
  @media (max-width: 1024px) {
    .hero {
      grid-template-columns: 1fr;
    }

    .games-grid {
      grid-template-columns: 1fr;
    }

    .stats-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    .findings-grid {
      grid-template-columns: 1fr;
    }

    .footer-content {
      grid-template-columns: 1fr;
      gap: 40px;
    }
  }
</style>
