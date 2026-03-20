<script>
    import { games, selectedGameId, phases, currentPhaseIndex, API_BASE } from '$lib/stores.js';

    async function loadGames() {
        const res = await fetch(`${API_BASE}/api/games`);
        $games = await res.json();
    }

    async function selectGame(gameId) {
        $selectedGameId = gameId;
        $currentPhaseIndex = 0;

        const res = await fetch(`${API_BASE}/api/games/${gameId}/phases`);
        $phases = await res.json();
    }

    loadGames();
</script>

<div class="game-selector">
    <select on:change={(e) => selectGame(e.target.value)} value={$selectedGameId || ''}>
        <option value="" disabled>Select a game...</option>
        {#each $games as game}
            <option value={game.id}>{game.id}</option>
        {/each}
    </select>
</div>

<style>
    .game-selector {
        display: flex;
        align-items: center;
    }

    select {
        padding: 8px 12px;
        font-size: 14px;
        border: 1px solid #444;
        border-radius: 4px;
        background: #2a2a2a;
        color: #fff;
        cursor: pointer;
        min-width: 300px;
    }

    select:focus {
        outline: none;
        border-color: #4a9eff;
    }
</style>
