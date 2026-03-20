<script>
    import { phases, currentPhaseIndex, currentPhase } from '$lib/stores.js';

    let isOpen = false;

    function prev() {
        if ($currentPhaseIndex > 0) {
            $currentPhaseIndex--;
        }
    }

    function next() {
        if ($currentPhaseIndex < $phases.length - 1) {
            $currentPhaseIndex++;
        }
    }

    function selectPhase(index) {
        $currentPhaseIndex = index;
        isOpen = false;
    }

    function toggleDropdown() {
        isOpen = !isOpen;
    }

    function formatSeason(season) {
        return season.charAt(0).toUpperCase() + season.slice(1);
    }

    function handleClickOutside(event) {
        if (isOpen && !event.target.closest('.phase-navigator')) {
            isOpen = false;
        }
    }
</script>

<svelte:window on:click={handleClickOutside} />

<div class="phase-navigator">
    <button class="nav-btn" on:click={prev} disabled={$currentPhaseIndex === 0}>
        <span class="arrow">&#8592;</span>
    </button>

    <div class="phase-dropdown">
        <button class="phase-display" on:click={toggleDropdown}>
            {#if $currentPhase}
                <span class="season">{formatSeason($currentPhase.season)}</span>
                <span class="year">{$currentPhase.year}</span>
                <span class="caret" class:open={isOpen}>&#9662;</span>
            {:else}
                <span class="placeholder">No phase selected</span>
            {/if}
        </button>

        {#if isOpen && $phases.length > 0}
            <div class="dropdown-list">
                {#each $phases as phase, index}
                    <button
                        class="dropdown-item"
                        class:active={index === $currentPhaseIndex}
                        on:click|stopPropagation={() => selectPhase(index)}
                    >
                        <span class="item-season">{formatSeason(phase.season)}</span>
                        <span class="item-year">{phase.year}</span>
                    </button>
                {/each}
            </div>
        {/if}
    </div>

    <button class="nav-btn" on:click={next} disabled={$currentPhaseIndex >= $phases.length - 1}>
        <span class="arrow">&#8594;</span>
    </button>
</div>

<style>
    .phase-navigator {
        display: flex;
        align-items: center;
        gap: 16px;
        background: #1a3a4a;
        padding: 8px 16px;
        border-radius: 4px;
    }

    .nav-btn {
        background: #2a4a5a;
        border: none;
        color: #fff;
        width: 36px;
        height: 36px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 18px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background 0.2s;
    }

    .nav-btn:hover:not(:disabled) {
        background: #3a5a6a;
    }

    .nav-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }

    .phase-dropdown {
        position: relative;
    }

    .phase-display {
        display: flex;
        gap: 8px;
        align-items: baseline;
        min-width: 150px;
        justify-content: center;
        background: transparent;
        border: none;
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 4px;
        transition: background 0.2s;
    }

    .phase-display:hover {
        background: rgba(255, 255, 255, 0.1);
    }

    .season {
        font-size: 16px;
        font-weight: 600;
        color: #fff;
        text-transform: uppercase;
    }

    .year {
        font-size: 20px;
        font-weight: 700;
        color: #4af;
    }

    .caret {
        color: #888;
        font-size: 12px;
        margin-left: 4px;
        transition: transform 0.2s;
    }

    .caret.open {
        transform: rotate(180deg);
    }

    .placeholder {
        color: #888;
        font-style: italic;
    }

    .dropdown-list {
        position: absolute;
        top: 100%;
        left: 50%;
        transform: translateX(-50%);
        margin-top: 8px;
        background: #2a2a2a;
        border: 1px solid #444;
        border-radius: 4px;
        max-height: 400px;
        overflow-y: auto;
        z-index: 100;
        min-width: 180px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
    }

    .dropdown-item {
        display: flex;
        gap: 8px;
        align-items: baseline;
        width: 100%;
        padding: 8px 16px;
        background: transparent;
        border: none;
        cursor: pointer;
        text-align: left;
        transition: background 0.15s;
    }

    .dropdown-item:hover {
        background: #3a3a3a;
    }

    .dropdown-item.active {
        background: #1a3a4a;
    }

    .item-season {
        font-size: 14px;
        font-weight: 500;
        color: #ccc;
        text-transform: uppercase;
        min-width: 60px;
    }

    .item-year {
        font-size: 14px;
        font-weight: 600;
        color: #4af;
    }
</style>
