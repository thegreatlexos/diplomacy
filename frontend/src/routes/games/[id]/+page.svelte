<script>
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { fetchGame, fetchGameModels, fetchSupplyCenters, fetchGameFiles, fetchPowerScores, fetchTurnMetrics, fetchGameEvents, getVisualizationUrl } from '$lib/api';
  import { formatModelName, generateGameTitle } from '$lib/gameUtils';

  let gameId = '';
  let game = null;
  let models = [];
  let powerScores = [];
  let turnMetrics = [];
  let gameEvents = [];
  let gameFiles = null;
  let pressMessages = {};
  let loading = true;
  let error = null;

  // Turn navigation
  let currentTurnIndex = 0;
  let currentVisualization = '';
  let currentTurnPress = [];
  let currentSummary = null;
  let currentOrders = null;
  let currentTurnMetrics = [];
  let showMetrics = false;
  let expandedPairs = {};
  let selectedYear = null;
  let yearSnapshot = null;

  $: gameId = $page.params.id;
  $: if (gameFiles && gameFiles.visualizations.length > 0) {
    currentVisualization = getVisualizationUrl(gameId, gameFiles.visualizations[currentTurnIndex]);
    currentTurnPress = getMessagesForTurn(currentTurnIndex);
    loadSummaryForTurn(currentTurnIndex);
    loadOrdersForTurn(currentTurnIndex);
    loadMetricsForTurn(currentTurnIndex);
  }

  function togglePair(pairKey) {
    expandedPairs[pairKey] = !expandedPairs[pairKey];
    expandedPairs = {...expandedPairs}; // Force reactivity
  }

  async function loadSummaryForTurn(turnIndex) {
    if (!gameFiles || !gameFiles.visualizations[turnIndex] || !gameFiles.summaries) return;

    const filename = gameFiles.visualizations[turnIndex];
    const match = filename.match(/(\d{4})_(spring|fall|winter)/);
    if (!match) {
      currentSummary = null;
      return;
    }

    const year = parseInt(match[1]);
    const season = match[2];
    const summaryFilename = `${year}_${season}_summary.md`;

    if (gameFiles.summaries.includes(summaryFilename)) {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      try {
        const response = await fetch(`${API_BASE_URL}/games/${gameId}/summaries/${summaryFilename}`);
        const text = await response.text();
        currentSummary = text;
      } catch (e) {
        console.error('Failed to load summary:', e);
        currentSummary = null;
      }
    } else {
      currentSummary = null;
    }
  }

  async function loadOrdersForTurn(turnIndex) {
    if (!gameFiles || !gameFiles.visualizations[turnIndex]) return;

    const filename = gameFiles.visualizations[turnIndex];
    const match = filename.match(/(\d{4})_(spring|fall|winter)/);
    if (!match) {
      currentOrders = null;
      return;
    }

    const year = parseInt(match[1]);
    const season = match[2];

    // Orders files are named like: 1901_spring_orders.json
    const ordersFilename = `${year}_${season}_orders.json`;

    if (gameFiles.orders && gameFiles.orders.includes(ordersFilename)) {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      try {
        const response = await fetch(`${API_BASE_URL}/games/${gameId}/orders/${ordersFilename}`);
        const data = await response.json();
        currentOrders = data;
      } catch (e) {
        console.error('Failed to load orders:', e);
        currentOrders = null;
      }
    } else {
      currentOrders = null;
    }
  }

  async function loadMetricsForTurn(turnIndex) {
    if (!gameFiles || !gameFiles.visualizations[turnIndex]) return;

    const filename = gameFiles.visualizations[turnIndex];
    const match = filename.match(/(\d{4})_(spring|fall|winter)/);
    if (!match) {
      currentTurnMetrics = [];
      return;
    }

    const year = parseInt(match[1]);
    const season = match[2];

    try {
      const metrics = await fetchTurnMetrics(gameId, year, season);
      currentTurnMetrics = metrics;
    } catch (e) {
      console.error('Failed to load turn metrics:', e);
      currentTurnMetrics = [];
    }
  }

  onMount(async () => {
    await loadGame();
  });

  async function loadGame() {
    loading = true;
    error = null;
    try {
      game = await fetchGame(gameId);
      models = await fetchGameModels(gameId);
      powerScores = await fetchPowerScores(gameId);
      gameEvents = await fetchGameEvents(gameId);
      gameFiles = await fetchGameFiles(gameId);

      // Load press messages if press game
      if (game.mode === 'press' && gameFiles.press.length > 0) {
        await loadPressMessages();
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load game';
      console.error('Failed to load game:', e);
    } finally {
      loading = false;
    }
  }

  async function loadPressMessages() {
    const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    for (const filename of gameFiles.press) {
      try {
        const response = await fetch(`${API_BASE_URL}/games/${gameId}/press/${filename}`);
        const text = await response.text();

        // Parse press file
        const messages = parsePressFile(text, filename);
        for (const msg of messages) {
          const key = `${msg.year}_${msg.season}`;
          if (!pressMessages[key]) {
            pressMessages[key] = [];
          }
          pressMessages[key].push(msg);
        }
      } catch (e) {
        console.error(`Failed to load press file ${filename}:`, e);
      }
    }
  }

  function parsePressFile(text, filename) {
    // Parse filename: power1_power2.txt
    // Known powers: england, france, germany, italy, austria-hungary, russia, turkey
    const withoutExt = filename.replace('.txt', '');

    const knownPowers = ['england', 'france', 'germany', 'italy', 'austria-hungary', 'russia', 'turkey'];

    let sender = '';
    let receiver = '';

    // Try to match known powers from the start
    for (const power of knownPowers) {
      if (withoutExt.startsWith(power + '_')) {
        sender = power;
        receiver = withoutExt.substring(power.length + 1);
        break;
      }
    }

    if (!sender) {
      console.error('Could not parse press filename:', filename);
      return [];
    }

    // Capitalize properly
    const capitalize = (str) => str.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('-');
    sender = capitalize(sender);
    receiver = capitalize(receiver);

    const messages = [];
    const lines = text.split('\n');
    let currentSeason = null;
    let currentYear = null;
    let currentRound = null;
    let currentSpeaker = null;
    let currentMessage = '';

    for (const line of lines) {
      // Match season header: [Spring 1905 - Press Round 1]
      const seasonMatch = line.match(/\[(Spring|Fall|Winter) (\d+) - Press Round (\d+)\]/);
      if (seasonMatch) {
        // Save previous message
        if (currentMessage && currentSpeaker) {
          messages.push({
            year: currentYear,
            season: currentSeason,
            round: currentRound,
            sender: currentSpeaker,
            receiver: currentSpeaker === sender ? receiver : sender,
            message: currentMessage.trim()
          });
        }

        currentSeason = seasonMatch[1].toLowerCase();
        currentYear = parseInt(seasonMatch[2]);
        currentRound = parseInt(seasonMatch[3]);
        currentMessage = '';
        currentSpeaker = null;
        continue;
      }

      // Match speaker: "Turkey: message"
      const speakerMatch = line.match(/^([A-Za-z-]+):\s*(.+)$/);
      if (speakerMatch) {
        // Save previous message
        if (currentMessage && currentSpeaker) {
          messages.push({
            year: currentYear,
            season: currentSeason,
            round: currentRound,
            sender: currentSpeaker,
            receiver: currentSpeaker === sender ? receiver : sender,
            message: currentMessage.trim()
          });
        }

        currentSpeaker = speakerMatch[1];
        currentMessage = speakerMatch[2];
      } else if (line.trim() && currentSpeaker) {
        // Continuation of message
        currentMessage += ' ' + line.trim();
      }
    }

    // Save final message
    if (currentMessage && currentSpeaker) {
      messages.push({
        year: currentYear,
        season: currentSeason,
        round: currentRound,
        sender: currentSpeaker,
        receiver: currentSpeaker === sender ? receiver : sender,
        message: currentMessage.trim()
      });
    }

    return messages;
  }

  function getMessagesForTurn(turnIndex) {
    if (!gameFiles || !gameFiles.visualizations[turnIndex]) return [];

    const filename = gameFiles.visualizations[turnIndex];
    const match = filename.match(/(\d{4})_(spring|fall|winter)/);
    if (!match) return [];

    const year = parseInt(match[1]);
    const season = match[2];
    const key = `${year}_${season}`;

    const messages = pressMessages[key] || [];

    // Group by nation pair
    const grouped = {};
    for (const msg of messages) {
      // Create consistent pair key (alphabetical order)
      const powers = [msg.sender, msg.receiver].sort();
      const pairKey = powers.join('_');

      if (!grouped[pairKey]) {
        grouped[pairKey] = {
          power1: powers[0],
          power2: powers[1],
          messages: []
        };
      }

      grouped[pairKey].messages.push(msg);
    }

    // Sort messages within each pair by round
    for (const pair of Object.values(grouped)) {
      pair.messages.sort((a, b) => a.round - b.round);
    }

    return Object.entries(grouped).map(([key, value]) => ({
      pairKey: key,
      ...value
    }));
  }

  function nextTurn() {
    if (gameFiles && currentTurnIndex < gameFiles.visualizations.length - 1) {
      currentTurnIndex++;
    }
  }

  function prevTurn() {
    if (currentTurnIndex > 0) {
      currentTurnIndex--;
    }
  }

  function parseTurnFromFilename(filename) {
    // Format: 001_1901_spring_00_initial.png
    const match = filename.match(/(\d{4})_(spring|fall|winter)/);
    if (match) {
      return `${match[2].toUpperCase()} ${match[1]}`;
    }
    return filename;
  }

  function getStatusColor(status) {
    switch (status) {
      case 'solo': return 'glow-green';
      case 'stalemate': return 'glow-amber';
      default: return 'glow-red';
    }
  }

  function getPowerColor(power) {
    const colors = {
      'England': '#1E3A8A',
      'France': '#60A5FA',
      'Germany': '#374151',
      'Italy': '#22C55E',
      'Austria-Hungary': '#DC2626',
      'Russia': '#FAFAFA',
      'Turkey': '#FBBF24'
    };
    return colors[power] || '#00FF41';
  }

  function getEventIcon(eventType) {
    const icons = {
      'game_start': '🎬',
      'territory_shift': '📍',
      'elimination': '☠️',
      'milestone': '👑',
      'victory': '🏆'
    };
    return icons[eventType] || '⚡';
  }

  function jumpToEvent(event) {
    // Find the turn index that matches this event's year/season
    if (!gameFiles) return;

    const targetPattern = `${event.year}_${event.season}`;
    const index = gameFiles.visualizations.findIndex(filename => filename.includes(targetPattern));

    if (index !== -1) {
      currentTurnIndex = index;
    }
  }

  function getTimelineYears() {
    if (!game) return [];
    const years = [];
    for (let year = game.start_year; year <= game.end_year; year++) {
      years.push(year);
    }
    return years;
  }

  async function showYearSnapshot(year) {
    selectedYear = year;

    try {
      const response = await fetchSupplyCenters(gameId);
      const yearData = response.filter(sc => sc.year === year);

      // Sort by SC count descending
      yearSnapshot = yearData.sort((a, b) => b.sc_count - a.sc_count);
    } catch (e) {
      console.error('Failed to load year snapshot:', e);
      yearSnapshot = null;
    }
  }

  function closeYearSnapshot() {
    selectedYear = null;
    yearSnapshot = null;
  }
</script>

<svelte:head>
  <title>{gameId} - Diplomacy AI Lab</title>
</svelte:head>

<div class="game-page">
  <!-- Header -->
  <header class="header">
    <div class="header-content">
      <div class="logo">
        <a href="/" class="terminal-prompt glow-green">DIPLOMACY_AI_LAB</a>
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

  <main class="main">
    {#if loading}
      <div class="loading-state">
        <p class="terminal-text glow-green">> LOADING GAME DATA</p>
      </div>
    {:else if error}
      <div class="error-state system-panel">
        <p class="terminal-text glow-red">ERROR: {error}</p>
        <a href="/games" class="back-link terminal-text">> BACK_TO_GAMES</a>
      </div>
    {:else if game}
      <div class="game-header">
        <a href="/games" class="back-link terminal-text glow-cyan">&lt; BACK</a>
        <h1 class="game-title terminal-prompt glow-green">{generateGameTitle(game, models)}</h1>
        <div class="game-subtitle terminal-text">{game.game_id}</div>
        <div class="game-badges">
          <span class="badge badge-{game.mode}">{game.mode.toUpperCase()}</span>
          <span class="badge badge-status {getStatusColor(game.status)}">{game.status.toUpperCase()}</span>
        </div>
      </div>

      <!-- Game Overview -->
      <section class="game-overview system-panel">
        <h2 class="section-title terminal-text">GAME_SUMMARY</h2>
        <div class="overview-grid">
          <div class="overview-item">
            <span class="label">WINNER</span>
            <span class="value hex-value">{game.winner}</span>
          </div>
          <div class="overview-item">
            <span class="label">MODEL</span>
            <span class="value">{formatModelName(game.winner_model)}</span>
          </div>
          <div class="overview-item">
            <span class="label">SUPPLY_CENTERS</span>
            <span class="value glow-cyan">{game.winner_scs}/34</span>
          </div>
          <div class="overview-item">
            <span class="label">DURATION</span>
            <span class="value">{game.end_year - game.start_year + 1} years</span>
          </div>
          <div class="overview-item">
            <span class="label">START_YEAR</span>
            <span class="value">{game.start_year}</span>
          </div>
          <div class="overview-item">
            <span class="label">END_YEAR</span>
            <span class="value">{game.end_year}</span>
          </div>
        </div>
      </section>

      <!-- Event Timeline -->
      {#if gameEvents.length > 0}
        <section class="timeline-section system-panel">
          <h2 class="section-title terminal-text">EVENT_TIMELINE</h2>
          <div class="timeline-container">
            <div class="timeline-track">
              {#each getTimelineYears() as year, i}
                {#if i > 0}
                  <div class="timeline-connector"></div>
                {/if}

                <!-- Year Marker -->
                <button
                  class="timeline-year"
                  on:click={() => showYearSnapshot(year)}
                  title="Click to view supply center distribution in {year}"
                >
                  <div class="year-marker">{year}</div>
                </button>

                <!-- Events for this year -->
                {@const yearEvents = gameEvents.filter(e => e.year === year)}
                {#if yearEvents.length > 0}
                  <div class="timeline-connector"></div>
                  {#each yearEvents as event, j}
                    <button
                      class="timeline-event event-{event.severity}"
                      on:click={() => jumpToEvent(event)}
                      title={event.description}
                    >
                      <div class="event-icon">{getEventIcon(event.event_type)}</div>
                      <div class="event-label">
                        <div class="event-type">{event.event_type.replace('_', ' ').toUpperCase()}</div>
                      </div>
                      {#if event.power}
                        <div class="event-power" style="background-color: {getPowerColor(event.power)}"></div>
                      {/if}
                    </button>
                    {#if j < yearEvents.length - 1}
                      <div class="timeline-connector short"></div>
                    {/if}
                  {/each}
                {/if}
              {/each}
            </div>
          </div>
          <div class="timeline-help terminal-text">
            <span class="glow-cyan">💡 TIP:</span> Click year markers for SC snapshot, events to jump to that moment
          </div>
        </section>
      {/if}

      <!-- Year Snapshot Modal -->
      {#if selectedYear && yearSnapshot}
        <div class="modal-overlay" on:click={closeYearSnapshot}>
          <div class="modal-content system-panel" on:click|stopPropagation>
            <div class="modal-header">
              <h3 class="modal-title terminal-text glow-green">SUPPLY CENTERS - {selectedYear}</h3>
              <button class="modal-close" on:click={closeYearSnapshot}>✕</button>
            </div>
            <div class="modal-body">
              {#each yearSnapshot as sc}
                <div class="sc-bar-container">
                  <div class="sc-power">
                    <span class="power-indicator" style="background-color: {getPowerColor(sc.power)};"></span>
                    <span class="power-name">{sc.power}</span>
                  </div>
                  <div class="sc-bar-track">
                    <div
                      class="sc-bar-fill"
                      style="width: {(sc.sc_count / 34) * 100}%; background-color: {getPowerColor(sc.power)};"
                    ></div>
                  </div>
                  <div class="sc-count glow-cyan">{sc.sc_count}</div>
                </div>
              {/each}
            </div>
          </div>
        </div>
      {/if}

      <!-- Turn Viewer -->
      {#if gameFiles && gameFiles.visualizations.length > 0}
        <section class="turn-viewer system-panel">
          <h2 class="section-title terminal-text">TURN_VIEWER</h2>

          <!-- Turn Navigation -->
          <div class="turn-navigation">
            <button
              class="nav-btn"
              on:click={prevTurn}
              disabled={currentTurnIndex === 0}
            >
              &lt; PREV
            </button>

            <div class="turn-info">
              <span class="turn-label terminal-text glow-cyan">
                {parseTurnFromFilename(gameFiles.visualizations[currentTurnIndex])}
              </span>
              <span class="turn-count">
                {currentTurnIndex + 1} / {gameFiles.visualizations.length}
              </span>
            </div>

            <button
              class="nav-btn"
              on:click={nextTurn}
              disabled={currentTurnIndex === gameFiles.visualizations.length - 1}
            >
              NEXT &gt;
            </button>
          </div>

          <!-- Map and Press Display -->
          <div class="viewer-layout">
            <!-- Map Display -->
            <div class="map-display">
              <img src={currentVisualization} alt="Turn visualization" />
            </div>

            <!-- Press Messages -->
            {#if game.mode === 'press'}
              <div class="press-panel">
                <h3 class="press-title terminal-text glow-amber">DIPLOMATIC_CORRESPONDENCE</h3>
                {#if currentTurnPress.length > 0}
                  <div class="press-pairs">
                    {#each currentTurnPress as pair}
                      <div class="press-pair">
                        <button
                          class="pair-header"
                          on:click={() => togglePair(pair.pairKey)}
                        >
                          <span class="pair-powers hex-value">
                            {pair.power1} ↔ {pair.power2}
                          </span>
                          <span class="message-count">
                            {pair.messages.length} msg{pair.messages.length !== 1 ? 's' : ''}
                          </span>
                          <span class="expand-icon">
                            {expandedPairs[pair.pairKey] ? '▼' : '▶'}
                          </span>
                        </button>

                        {#if expandedPairs[pair.pairKey]}
                          <div class="pair-messages">
                            {#each pair.messages as msg}
                              <div class="press-message">
                                <div class="msg-header">
                                  <span class="msg-sender">{msg.sender}:</span>
                                  <span class="msg-round">Round {msg.round}</span>
                                </div>
                                <div class="msg-content">{msg.message}</div>
                              </div>
                            {/each}
                          </div>
                        {/if}
                      </div>
                    {/each}
                  </div>
                {:else}
                  <p class="no-press terminal-text">No messages this turn</p>
                {/if}
              </div>
            {/if}
          </div>

          <!-- Metrics Toggle -->
          <div class="metrics-toggle">
            <button class="toggle-btn" on:click={() => showMetrics = !showMetrics}>
              {showMetrics ? '▼' : '▶'} {showMetrics ? 'HIDE' : 'SHOW'}_DETAILED_METRICS
            </button>
          </div>

          <!-- Orders & Metrics Panel -->
          {#if showMetrics}
            <div class="metrics-panel system-panel">
              <h3 class="metrics-title terminal-text glow-amber">TACTICAL_METRICS_&_ORDERS</h3>

              <!-- Turn Metrics Summary -->
              {#if currentTurnMetrics.length > 0}
                <div class="metrics-grid">
                  {#each currentTurnMetrics as metric}
                    {@const powerScore = powerScores.find(ps => ps.power === metric.power)}
                    <div class="metric-card">
                      <div class="metric-header">
                        <span class="power-indicator" style="background-color: {getPowerColor(metric.power)};"></span>
                        <span class="hex-value">{metric.power}</span>
                      </div>
                      <div class="metric-stats">
                        <div class="stat-row">
                          <span class="stat-label">Invalid Orders:</span>
                          <span class="stat-value {metric.invalid_orders > 5 ? 'glow-red' : metric.invalid_orders > 0 ? 'glow-amber' : 'glow-green'}">
                            {metric.invalid_orders}
                          </span>
                        </div>
                        <div class="stat-row">
                          <span class="stat-label">Bounces:</span>
                          <span class="stat-value {metric.bounces > 3 ? 'glow-amber' : ''}">{metric.bounces}</span>
                        </div>
                        <div class="stat-row">
                          <span class="stat-label">Supports:</span>
                          <span class="stat-value glow-cyan">{metric.supports_own + metric.supports_other}</span>
                        </div>
                        <div class="stat-row">
                          <span class="stat-label">Convoys:</span>
                          <span class="stat-value">{metric.convoys}</span>
                        </div>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}

              <!-- Orders Display -->
              {#if currentOrders}
                <div class="orders-by-power">
                  {#each Object.entries(groupOrdersByPower(currentOrders)) as [power, orders]}
                    <div class="power-orders">
                      <div class="power-orders-header">
                        <span class="power-indicator" style="background-color: {getPowerColor(power)};"></span>
                        <span class="hex-value">{power}</span>
                      </div>
                      <div class="orders-list">
                        {#each orders as order}
                          <div class="order-item {order.is_invalid ? 'invalid-order' : ''}">
                            <span class="order-unit">{order.unit || order.Unit}:</span>
                            <span class="order-action">{formatOrder(order)}</span>
                            {#if order.is_invalid || order.invalid}
                              <span class="invalid-badge">INVALID</span>
                            {/if}
                          </div>
                        {/each}
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}
            </div>
          {/if}

          <!-- Turn Summary -->
          {#if currentSummary}
            <div class="turn-summary">
              <h3 class="summary-title terminal-text glow-green">AI_GENERATED_SUMMARY</h3>
              <div class="summary-content">
                {@html currentSummary
                  .replace(/^# (.+)$/gm, '<h4 class="summary-heading">$1</h4>')
                  .replace(/^## (.+)$/gm, '<h5 class="summary-subheading">$1</h5>')
                  .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                  .replace(/\*(.+?)\*/g, '<em>$1</em>')
                  .replace(/```[\s\S]*?```/g, (match) => `<pre class="summary-code">${match.replace(/```/g, '')}</pre>`)
                  .replace(/^- (.+)$/gm, '<li>$1</li>')
                  .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
                  .replace(/\n\n/g, '</p><p>')
                  .replace(/^(?!<[huplsi])/gm, '<p>')
                  .replace(/(?<![>])\n$/gm, '</p>')
                }
              </div>
            </div>
          {/if}
        </section>
      {/if}

      <!-- Models/Powers -->
      <section class="models-section system-panel">
        <h2 class="section-title terminal-text">POWER_ASSIGNMENTS</h2>
        <div class="models-grid">
          {#each models.sort((a, b) => (a.final_rank || 99) - (b.final_rank || 99)) as model}
            {@const powerScore = powerScores.find(ps => ps.power === model.power)}
            <div class="model-card">
              <div class="model-header">
                <span class="power-name hex-value">{model.power}</span>
                {#if model.final_rank}
                  <span class="rank glow-amber">RANK #{model.final_rank}</span>
                {/if}
              </div>
              <div class="model-info">
                <div class="info-row">
                  <span class="label">MODEL:</span>
                  <span class="value">{formatModelName(model.model_id)}</span>
                </div>
                <div class="info-row">
                  <span class="label">PROVIDER:</span>
                  <span class="value">{model.provider.toUpperCase()}</span>
                </div>
                <div class="info-row">
                  <span class="label">TIER:</span>
                  <span class="value tier-{model.tier}">{model.tier.toUpperCase()}</span>
                </div>
                <div class="info-row">
                  <span class="label">FINAL_SCs:</span>
                  <span class="value glow-cyan">{model.final_scs}</span>
                </div>

                {#if powerScore}
                  <div class="info-section-divider"></div>
                  <div class="info-row">
                    <span class="label">TOTAL_SCORE:</span>
                    <span class="value {powerScore.total_score > 200 ? 'glow-green' : powerScore.total_score < 0 ? 'glow-red' : ''}">{powerScore.total_score}</span>
                  </div>
                  <div class="info-row">
                    <span class="label">INVALID_ORDERS:</span>
                    <span class="value {powerScore.total_invalid_orders > 10 ? 'glow-red' : powerScore.total_invalid_orders > 5 ? 'glow-amber' : 'glow-green'}">{powerScore.total_invalid_orders}</span>
                  </div>
                  <div class="info-row">
                    <span class="label">BOUNCES:</span>
                    <span class="value">{powerScore.total_bounces}</span>
                  </div>
                  <div class="info-row">
                    <span class="label">SUPPORTS:</span>
                    <span class="value glow-cyan">{powerScore.total_supports_own + powerScore.total_supports_other}</span>
                  </div>
                {/if}

                {#if model.deception_score !== null}
                  <div class="info-section-divider"></div>
                  <div class="info-row">
                    <span class="label">DECEPTION:</span>
                    <span class="value glow-amber">{model.deception_score.toFixed(1)}/10</span>
                  </div>
                {/if}
                {#if model.truthfulness_score !== null}
                  <div class="info-row">
                    <span class="label">TRUTHFULNESS:</span>
                    <span class="value glow-green">{model.truthfulness_score.toFixed(1)}/10</span>
                  </div>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </section>
    {/if}
  </main>
</div>

<style>
  .game-page {
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

  /* Main */
  .main {
    padding: 100px 24px 60px;
    max-width: 1400px;
    margin: 0 auto;
  }

  .loading-state,
  .error-state {
    padding: 60px 24px;
    text-align: center;
  }

  .back-link {
    display: inline-block;
    margin-bottom: 24px;
    font-size: 14px;
    text-decoration: none;
  }

  .back-link:hover {
    text-decoration: underline;
  }

  .game-header {
    margin-bottom: 40px;
  }

  .game-title {
    font-size: 36px;
    font-weight: 700;
    margin-bottom: 8px;
  }

  .game-subtitle {
    font-size: 12px;
    color: var(--text-dim);
    margin-bottom: 16px;
  }

  .game-badges {
    display: flex;
    gap: 12px;
  }

  .badge {
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 700;
    border: 1px solid var(--border-color);
    text-transform: uppercase;
  }

  .badge-gunboat {
    color: var(--accent-amber);
    border-color: var(--accent-amber);
  }

  .badge-press {
    color: var(--accent-cyan);
    border-color: var(--accent-cyan);
  }

  .badge-platform {
    color: var(--text-dim);
  }

  /* Overview */
  .game-overview {
    padding: 32px;
    margin-bottom: 32px;
  }

  /* Turn Viewer */
  .turn-viewer {
    padding: 32px;
    margin-bottom: 32px;
  }

  .turn-navigation {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-color);
  }

  .nav-btn {
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    padding: 8px 20px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    font-family: inherit;
  }

  .nav-btn:hover:not(:disabled) {
    border-color: var(--accent-green);
    color: var(--accent-green);
  }

  .nav-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .turn-info {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }

  .turn-label {
    font-size: 16px;
    font-weight: 700;
  }

  .turn-count {
    font-size: 11px;
    color: var(--text-dim);
  }

  .viewer-layout {
    display: grid;
    grid-template-columns: 1fr 400px;
    gap: 24px;
  }

  .map-display {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    padding: 16px;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 400px;
  }

  .map-display img {
    max-width: 100%;
    height: auto;
    display: block;
  }

  .press-panel {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    padding: 16px;
    max-height: 600px;
    overflow-y: auto;
  }

  .press-title {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-color);
  }

  .press-pairs {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .press-pair {
    border: 1px solid var(--border-color);
  }

  .pair-header {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: rgba(0, 255, 65, 0.02);
    border: none;
    cursor: pointer;
    font-family: inherit;
    transition: all 0.2s;
  }

  .pair-header:hover {
    background: rgba(0, 255, 65, 0.05);
  }

  .pair-powers {
    font-size: 12px;
    font-weight: 700;
  }

  .message-count {
    font-size: 10px;
    color: var(--text-dim);
  }

  .expand-icon {
    margin-left: auto;
    color: var(--accent-green);
    font-size: 10px;
  }

  .pair-messages {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px;
    background: var(--bg-primary);
  }

  .press-message {
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
  }

  .press-message:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }

  .msg-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 6px;
    font-size: 11px;
  }

  .msg-sender {
    font-weight: 700;
    color: var(--accent-cyan);
  }

  .msg-round {
    color: var(--text-dim);
    font-size: 10px;
  }

  .msg-content {
    font-size: 12px;
    line-height: 1.6;
    color: var(--text-secondary);
  }

  .no-press {
    text-align: center;
    padding: 40px 20px;
    color: var(--text-dim);
    font-size: 12px;
  }

  /* Turn Summary */
  .turn-summary {
    margin-top: 24px;
    padding: 24px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
  }

  .summary-title {
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-color);
  }

  .summary-content {
    font-size: 13px;
    line-height: 1.8;
    color: var(--text-secondary);
  }

  .summary-content :global(h4) {
    font-size: 18px;
    color: var(--accent-cyan);
    margin: 24px 0 12px 0;
    font-weight: 700;
  }

  .summary-content :global(h5) {
    font-size: 14px;
    color: var(--accent-green);
    margin: 16px 0 8px 0;
    font-weight: 700;
  }

  .summary-content :global(p) {
    margin-bottom: 12px;
  }

  .summary-content :global(strong) {
    color: var(--text-primary);
    font-weight: 700;
  }

  .summary-content :global(em) {
    color: var(--accent-amber);
    font-style: italic;
  }

  .summary-content :global(ul) {
    margin: 12px 0;
    padding-left: 24px;
  }

  .summary-content :global(li) {
    margin-bottom: 6px;
  }

  .summary-content :global(pre) {
    background: rgba(0, 255, 65, 0.05);
    border: 1px solid var(--border-color);
    padding: 12px;
    margin: 12px 0;
    overflow-x: auto;
    font-size: 11px;
    font-family: var(--font-mono);
  }

  @media (max-width: 1200px) {
    .viewer-layout {
      grid-template-columns: 1fr;
    }

    .press-panel {
      max-height: 400px;
    }
  }

  .section-title {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 24px;
    color: var(--accent-green);
  }

  .overview-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 24px;
  }

  .overview-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .overview-item .label {
    font-size: 11px;
    color: var(--text-dim);
    text-transform: uppercase;
  }

  .overview-item .value {
    font-size: 16px;
    font-weight: 600;
  }

  /* Models */
  .models-section {
    padding: 32px;
  }

  .models-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 16px;
  }

  .model-card {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    padding: 16px;
  }

  .model-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-color);
  }

  .power-name {
    font-size: 14px;
    font-weight: 700;
  }

  .rank {
    font-size: 12px;
  }

  .model-info {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .info-row {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
  }

  .info-row .label {
    color: var(--text-dim);
  }

  .info-row .value {
    color: var(--text-primary);
    font-weight: 500;
  }

  .info-section-divider {
    height: 1px;
    background: var(--border-color);
    margin: 8px 0;
  }

  .tier-premium {
    color: var(--accent-green) !important;
  }

  .tier-mid {
    color: var(--accent-cyan) !important;
  }

  .tier-budget {
    color: var(--accent-amber) !important;
  }

  /* Event Timeline */
  .timeline-section {
    padding: 32px;
    margin-bottom: 32px;
  }

  .timeline-container {
    overflow-x: auto;
    overflow-y: hidden;
    padding: 24px 0;
    margin: 0 -16px;
    padding: 24px 16px;
  }

  .timeline-track {
    display: flex;
    align-items: center;
    min-width: max-content;
    padding-bottom: 8px;
  }

  .timeline-event {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    padding: 12px;
    background: var(--bg-primary);
    border: 2px solid var(--border-color);
    cursor: pointer;
    transition: all 0.2s;
    min-width: 120px;
  }

  .timeline-event:hover {
    transform: translateY(-4px);
    border-color: var(--accent-cyan);
    box-shadow: 0 4px 12px rgba(0, 255, 255, 0.2);
  }

  .timeline-event.event-high {
    border-color: var(--accent-amber);
  }

  .timeline-event.event-critical {
    border-color: var(--accent-green);
  }

  .event-icon {
    font-size: 24px;
    filter: drop-shadow(0 0 4px currentColor);
  }

  .event-label {
    text-align: center;
  }

  .event-year {
    font-size: 14px;
    font-weight: 700;
    color: var(--accent-cyan);
  }

  .event-type {
    font-size: 9px;
    color: var(--text-dim);
    text-transform: uppercase;
    margin-top: 4px;
  }

  .event-power {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    position: absolute;
    top: 8px;
    right: 8px;
  }

  .timeline-connector {
    width: 24px;
    height: 2px;
    background: var(--border-color);
    flex-shrink: 0;
  }

  .timeline-connector.short {
    width: 8px;
  }

  .timeline-year {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 8px 16px;
    background: transparent;
    border: 1px solid var(--border-color);
    cursor: pointer;
    transition: all 0.2s;
    min-width: 80px;
  }

  .timeline-year:hover {
    border-color: var(--accent-green);
    background: rgba(0, 255, 65, 0.05);
  }

  .year-marker {
    font-size: 16px;
    font-weight: 700;
    color: var(--accent-green);
  }

  .timeline-help {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--border-color);
    font-size: 12px;
    text-align: center;
  }

  /* Modal */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
    backdrop-filter: blur(4px);
  }

  .modal-content {
    max-width: 600px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
    padding: 24px;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-color);
  }

  .modal-title {
    font-size: 18px;
    font-weight: 700;
  }

  .modal-close {
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--text-secondary);
    font-size: 20px;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;
  }

  .modal-close:hover {
    border-color: var(--accent-red);
    color: var(--accent-red);
  }

  .modal-body {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .sc-bar-container {
    display: grid;
    grid-template-columns: 140px 1fr 50px;
    gap: 12px;
    align-items: center;
    padding: 8px;
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
  }

  .sc-power {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    font-weight: 600;
  }

  .sc-bar-track {
    height: 20px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border-color);
    position: relative;
    overflow: hidden;
  }

  .sc-bar-fill {
    height: 100%;
    transition: width 0.3s ease;
    opacity: 0.8;
  }

  .sc-count {
    font-size: 14px;
    font-weight: 700;
    text-align: right;
  }

  /* Metrics Panel */
  .metrics-panel {
    margin-top: 24px;
    padding: 24px;
  }

  .metrics-title {
    font-size: 16px;
    font-weight: 700;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-color);
  }

  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 32px;
  }

  .metric-card {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    padding: 12px;
  }

  .metric-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
  }

  .power-indicator {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    flex-shrink: 0;
  }

  .metric-stats {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .stat-row {
    display: flex;
    justify-content: space-between;
    font-size: 11px;
  }

  .stat-label {
    color: var(--text-dim);
  }

  .stat-value {
    font-weight: 600;
  }

  .metrics-toggle {
    margin-top: 24px;
    padding: 16px 0;
    border-top: 1px solid var(--border-color);
  }

  .toggle-btn {
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--accent-cyan);
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
  }

  .toggle-btn:hover {
    border-color: var(--accent-cyan);
    background: rgba(0, 255, 255, 0.05);
  }

  .orders-by-power {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .power-orders {
    background: var(--bg-primary);
    border: 1px solid var(--border-color);
    padding: 12px;
  }

  .power-orders-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 10px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
  }

  .orders-list {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .order-item {
    font-size: 11px;
    padding: 6px;
    background: rgba(0, 255, 65, 0.02);
    border-left: 2px solid var(--accent-green);
  }

  .order-item.invalid-order {
    background: rgba(255, 0, 0, 0.1);
    border-left-color: var(--accent-red);
  }

  .order-unit {
    font-weight: 700;
    color: var(--accent-cyan);
  }

  .order-action {
    color: var(--text-secondary);
  }

  .invalid-badge {
    margin-left: 8px;
    padding: 2px 6px;
    background: var(--accent-red);
    color: var(--bg-primary);
    font-size: 9px;
    font-weight: 700;
    border-radius: 2px;
  }
</style>
