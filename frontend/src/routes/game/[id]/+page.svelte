<script>
  import GameSelector from '$lib/components/GameSelector.svelte';
  import PhaseNavigator from '$lib/components/PhaseNavigator.svelte';
  import OrdersTab from '$lib/components/OrdersTab.svelte';
  import PressTab from '$lib/components/PressTab.svelte';
  import SummaryTab from '$lib/components/SummaryTab.svelte';
  import YearlyScoresTab from '$lib/components/YearlyScoresTab.svelte';
  import { selectedGameId, currentPhase, API_BASE } from '$lib/stores.js';
  import { page } from '$app/stores';
  import { onMount } from 'svelte';

  let activeTab = 'orders';

  onMount(() => {
    const gameId = $page.params.id;
    selectedGameId.set(gameId);
  });

  $: visualizationUrl = $currentPhase?.visualization_path
      ? `${API_BASE}${$currentPhase.visualization_path}`
      : null;

  function shareToTwitter() {
    const text = `Check out this AI Diplomacy game: ${$selectedGameId}`;
    const url = window.location.href;
    window.open(`https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`, '_blank');
  }

  function shareToLinkedIn() {
    const url = window.location.href;
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`, '_blank');
  }

  function copyLink() {
    navigator.clipboard.writeText(window.location.href);
    alert('Link copied to clipboard!');
  }
</script>

<svelte:head>
  <title>{$selectedGameId || 'Game'} // DIPLOMACY_AI_LAB</title>
</svelte:head>

<div class="game-viewer">
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

  <!-- Subheader with game controls -->
  <div class="subheader">
    <div class="subheader-content">
      <div class="subheader-left">
        <a href="/games" class="back-link terminal-text glow-cyan">
          &lt; BACK TO ARCHIVE
        </a>
        <div class="game-selector-container">
          <GameSelector />
        </div>
      </div>
      <div class="subheader-right">
        <PhaseNavigator />
      </div>
    </div>
  </div>

  <!-- Main content -->
  <main class="main">
    {#if !$selectedGameId}
      <div class="loading terminal-text glow-green">
        > LOADING SIMULATION<span class="cursor-blink"></span>
      </div>
    {:else}
      <!-- Left panel: Map visualization -->
      <div class="left-panel">
        {#if visualizationUrl}
          <img src={visualizationUrl} alt="Game map" class="map-image" />
        {:else}
          <div class="no-map terminal-text">
            > NO VISUALIZATION AVAILABLE FOR THIS PHASE
          </div>
        {/if}

        <!-- Share buttons -->
        <div class="share-panel system-panel">
          <div class="system-panel-title">SHARE_SIMULATION</div>
          <div class="share-buttons">
            <button on:click={shareToTwitter} class="share-btn">
              <span class="terminal-text">TWITTER</span>
            </button>
            <button on:click={shareToLinkedIn} class="share-btn">
              <span class="terminal-text">LINKEDIN</span>
            </button>
            <button on:click={copyLink} class="share-btn">
              <span class="terminal-text">COPY_LINK</span>
            </button>
          </div>
        </div>
      </div>

      <!-- Right panel: Tabs -->
      <div class="right-panel">
        <div class="tabs">
          <button
            class="tab terminal-text"
            class:active={activeTab === 'orders'}
            on:click={() => activeTab = 'orders'}
          >
            ORDERS
          </button>
          <button
            class="tab terminal-text"
            class:active={activeTab === 'press'}
            on:click={() => activeTab = 'press'}
          >
            PRESS
          </button>
          <button
            class="tab terminal-text"
            class:active={activeTab === 'summary'}
            on:click={() => activeTab = 'summary'}
          >
            SUMMARY
          </button>
          <button
            class="tab terminal-text"
            class:active={activeTab === 'yearly'}
            on:click={() => activeTab = 'yearly'}
          >
            YEARLY
          </button>
        </div>

        <div class="tab-content">
          {#if activeTab === 'orders'}
            <OrdersTab />
          {:else if activeTab === 'press'}
            <PressTab />
          {:else if activeTab === 'summary'}
            <SummaryTab />
          {:else if activeTab === 'yearly'}
            <YearlyScoresTab />
          {/if}
        </div>
      </div>
    {/if}
  </main>
</div>

<style>
  .game-viewer {
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
    max-width: 1800px;
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

  /* Subheader */
  .subheader {
    position: fixed;
    top: 57px;
    left: 0;
    right: 0;
    background: var(--bg-tertiary);
    border-bottom: 1px solid var(--border-color);
    z-index: 999;
  }

  .subheader-content {
    max-width: 1800px;
    margin: 0 auto;
    padding: 12px 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .subheader-left {
    display: flex;
    align-items: center;
    gap: 24px;
  }

  .back-link {
    font-size: 13px;
    text-decoration: none;
  }

  .game-selector-container {
    border-left: 1px solid var(--border-color);
    padding-left: 24px;
  }

  /* Main content */
  .main {
    padding-top: 120px;
    display: flex;
    height: calc(100vh - 120px);
    max-width: 1800px;
    margin: 0 auto;
  }

  .loading {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
  }

  .left-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 16px;
    background: var(--bg-secondary);
    padding: 16px;
    overflow: auto;
  }

  .map-image {
    max-width: 100%;
    height: auto;
    border: 1px solid var(--border-color);
    border-radius: 4px;
  }

  .no-map {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
  }

  .share-panel {
    padding: 16px;
  }

  .share-buttons {
    display: flex;
    gap: 8px;
  }

  .share-btn {
    flex: 1;
    padding: 10px;
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--accent-green);
    cursor: pointer;
    transition: all 0.2s;
    font-family: var(--font-mono);
    font-size: 11px;
  }

  .share-btn:hover {
    border-color: var(--accent-green);
    box-shadow: 0 0 15px var(--border-glow);
  }

  /* Right panel - tabs */
  .right-panel {
    width: 600px;
    display: flex;
    flex-direction: column;
    border-left: 1px solid var(--border-color);
    background: var(--bg-tertiary);
  }

  .tabs {
    display: flex;
    border-bottom: 1px solid var(--border-color);
    background: var(--bg-secondary);
  }

  .tab {
    flex: 1;
    padding: 14px;
    background: transparent;
    border: none;
    color: var(--text-dim);
    cursor: pointer;
    font-size: 12px;
    font-weight: 500;
    transition: all 0.2s;
    font-family: var(--font-mono);
  }

  .tab:hover {
    color: var(--accent-green);
    background: var(--bg-tertiary);
  }

  .tab.active {
    color: var(--accent-green);
    background: var(--bg-tertiary);
    border-bottom: 2px solid var(--accent-green);
  }

  .tab-content {
    flex: 1;
    overflow: hidden;
  }

  @media (max-width: 1200px) {
    .main {
      flex-direction: column;
      height: auto;
    }

    .right-panel {
      width: 100%;
    }
  }
</style>
