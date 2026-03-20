<script>
    import GameSelector from '$lib/components/GameSelector.svelte';
    import PhaseNavigator from '$lib/components/PhaseNavigator.svelte';
    import OrdersTab from '$lib/components/OrdersTab.svelte';
    import PressTab from '$lib/components/PressTab.svelte';
    import SummaryTab from '$lib/components/SummaryTab.svelte';
    import { selectedGameId, currentPhase, API_BASE } from '$lib/stores.js';

    let activeTab = 'orders';

    $: visualizationUrl = $currentPhase?.visualization_path
        ? `${API_BASE}${$currentPhase.visualization_path}`
        : null;
</script>

<div class="app">
    <!-- Header -->
    <header class="header">
        <div class="header-left">
            <PhaseNavigator />
        </div>
        <div class="header-right">
            <GameSelector />
        </div>
    </header>

    <!-- Main content -->
    <main class="main">
        {#if !$selectedGameId}
            <div class="welcome">
                <h1>Diplomacy Game Viewer</h1>
                <p>Select a game from the dropdown to begin</p>
            </div>
        {:else}
            <!-- Left panel: Map visualization -->
            <div class="left-panel">
                {#if visualizationUrl}
                    <img src={visualizationUrl} alt="Game map" class="map-image" />
                {:else}
                    <div class="no-map">
                        <p>No visualization available for this phase</p>
                    </div>
                {/if}
            </div>

            <!-- Right panel: Tabs -->
            <div class="right-panel">
                <div class="tabs">
                    <button
                        class="tab"
                        class:active={activeTab === 'orders'}
                        on:click={() => activeTab = 'orders'}
                    >
                        Orders
                    </button>
                    <button
                        class="tab"
                        class:active={activeTab === 'press'}
                        on:click={() => activeTab = 'press'}
                    >
                        Press
                    </button>
                    <button
                        class="tab"
                        class:active={activeTab === 'summary'}
                        on:click={() => activeTab = 'summary'}
                    >
                        Summary
                    </button>
                </div>

                <div class="tab-content">
                    {#if activeTab === 'orders'}
                        <OrdersTab />
                    {:else if activeTab === 'press'}
                        <PressTab />
                    {:else if activeTab === 'summary'}
                        <SummaryTab />
                    {/if}
                </div>
            </div>
        {/if}
    </main>
</div>

<style>
    :global(*) {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }

    :global(body) {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: #1a1a1a;
        color: #fff;
    }

    .app {
        display: flex;
        flex-direction: column;
        height: 100vh;
    }

    .header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 20px;
        background: #111;
        border-bottom: 1px solid #333;
    }

    .header-left {
        display: flex;
        align-items: center;
        gap: 20px;
    }

    .header-right {
        display: flex;
        align-items: center;
    }

    .main {
        flex: 1;
        display: flex;
        overflow: hidden;
    }

    .welcome {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        color: #666;
    }

    .welcome h1 {
        font-size: 32px;
        margin-bottom: 16px;
        color: #888;
    }

    .left-panel {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        background: #111;
        padding: 8px;
        overflow: auto;
    }

    .tabs {
        display: flex;
        border-bottom: 1px solid #333;
    }

    .tab {
        flex: 1;
        padding: 12px;
        background: transparent;
        border: none;
        color: #888;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.2s;
    }

    .tab:hover {
        color: #fff;
        background: #2a2a2a;
    }

    .tab.active {
        color: #4af;
        border-bottom: 2px solid #4af;
    }

    .tab-content {
        flex: 1;
        overflow: hidden;
    }

    .right-panel {
        width: 550px;
        display: flex;
        flex-direction: column;
        border-left: 1px solid #333;
        background: #1e1e1e;
    }

    .map-image {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        border-radius: 4px;
    }

    .no-map {
        color: #666;
        text-align: center;
    }
</style>
