<script>
    import { selectedGameId, API_BASE } from '$lib/stores.js';

    let yearlyMetrics = { sc_counts: {}, precision: {} };
    let modelAssignments = null;
    let loading = true;

    const powers = ['England', 'France', 'Germany', 'Italy', 'Austria-Hungary', 'Russia', 'Turkey'];
    const powerAbbrev = {
        'England': 'ENG',
        'France': 'FRA',
        'Germany': 'GER',
        'Italy': 'ITA',
        'Austria-Hungary': 'AUS',
        'Russia': 'RUS',
        'Turkey': 'TUR'
    };

    const powerColors = {
        'England': '#2563eb',
        'France': '#60a5fa',
        'Germany': '#4b5563',
        'Italy': '#22c55e',
        'Austria-Hungary': '#ef4444',
        'Russia': '#a855f7',
        'Turkey': '#f59e0b'
    };

    $: if ($selectedGameId) {
        loadData();
    }

    async function loadData() {
        loading = true;
        try {
            const [metricsRes, assignmentsRes] = await Promise.all([
                fetch(`${API_BASE}/api/games/${$selectedGameId}/yearly-metrics`),
                fetch(`${API_BASE}/api/games/${$selectedGameId}/model-assignments`)
            ]);
            yearlyMetrics = await metricsRes.json();
            modelAssignments = await assignmentsRes.json();
        } catch (e) {
            yearlyMetrics = { sc_counts: {}, precision: {} };
            modelAssignments = null;
        }
        loading = false;
    }

    function getYears() {
        return Object.keys(yearlyMetrics.sc_counts || {}).sort((a, b) => parseInt(a) - parseInt(b));
    }

    function getSC(year, power) {
        return yearlyMetrics.sc_counts?.[year]?.[power] ?? '-';
    }

    function getPrevSC(years, yearIndex, power) {
        if (yearIndex === 0) return null;
        const prevYear = years[yearIndex - 1];
        return yearlyMetrics.sc_counts?.[prevYear]?.[power] ?? null;
    }

    function getChangeClass(current, prev) {
        if (prev === null || current === '-') return '';
        if (current > prev) return 'up';
        if (current < prev) return 'down';
        return '';
    }

    function shortenModel(modelId) {
        if (!modelId) return 'N/A';
        // OpenRouter format
        if (modelId.includes('/')) {
            return modelId.split('/').pop();
        }
        // Bedrock format
        if (modelId.includes('haiku')) return 'Haiku 4.5';
        if (modelId.includes('sonnet')) return 'Sonnet 4.6';
        if (modelId.includes('opus')) return 'Opus 4.6';
        return modelId;
    }
</script>

<div class="yearly-tab">
    {#if loading}
        <p class="loading">Loading metrics...</p>
    {:else if getYears().length === 0}
        <p class="empty">No yearly metrics available</p>
    {:else}
        <div class="table-container">
            <table class="sc-table">
                <thead>
                    <tr>
                        <th class="year-col">Year</th>
                        {#each powers as power}
                            <th style="--power-color: {powerColors[power]}">{powerAbbrev[power]}</th>
                        {/each}
                    </tr>
                </thead>
                <tbody>
                    {#each getYears() as year, i}
                        <tr>
                            <td class="year-col">{year}</td>
                            {#each powers as power}
                                {@const sc = getSC(year, power)}
                                {@const prev = getPrevSC(getYears(), i, power)}
                                {@const changeClass = getChangeClass(sc, prev)}
                                <td class="sc-cell {changeClass}" class:eliminated={sc === 0}>
                                    {sc}
                                </td>
                            {/each}
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>

        <!-- Model Legend -->
        {#if modelAssignments?.assignments}
            <div class="legend">
                <h4>Model Assignments</h4>
                <div class="legend-grid">
                    {#each powers as power}
                        <div class="legend-item">
                            <span class="power-marker" style="--power-color: {powerColors[power]}"></span>
                            <span class="power-label">{powerAbbrev[power]}</span>
                            <span class="model-label">{shortenModel(modelAssignments.assignments[power])}</span>
                        </div>
                    {/each}
                </div>
                {#if modelAssignments.gunboat_mode}
                    <div class="mode-badge gunboat">Gunboat Mode</div>
                {:else}
                    <div class="mode-badge press">Press Enabled</div>
                {/if}
            </div>
        {/if}
    {/if}
</div>

<style>
    .yearly-tab {
        padding: 16px;
        height: 100%;
        overflow-y: auto;
    }

    .loading, .empty {
        color: #888;
        text-align: center;
        padding: 32px;
    }

    .table-container {
        overflow-x: auto;
    }

    .sc-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 12px;
        font-family: monospace;
    }

    .sc-table th {
        background: #1a1a1a;
        color: #fff;
        padding: 8px 6px;
        text-align: center;
        border-bottom: 2px solid var(--power-color, #333);
        font-weight: 600;
    }

    .sc-table td {
        padding: 6px;
        text-align: center;
        border-bottom: 1px solid #333;
        color: #ccc;
    }

    .year-col {
        text-align: left !important;
        font-weight: 500;
        color: #888;
        width: 60px;
    }

    .sc-cell {
        transition: background 0.2s;
    }

    .sc-cell.up {
        color: #4ade80;
        font-weight: 600;
    }

    .sc-cell.down {
        color: #f87171;
    }

    .sc-cell.eliminated {
        color: #666;
        background: #1a1a1a;
    }

    /* Legend */
    .legend {
        margin-top: 24px;
        padding: 16px;
        background: #1a1a1a;
        border-radius: 8px;
    }

    .legend h4 {
        margin: 0 0 12px 0;
        color: #888;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .legend-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: 8px;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 8px;
        background: #222;
        border-radius: 4px;
    }

    .power-marker {
        width: 10px;
        height: 10px;
        background: var(--power-color);
        border-radius: 2px;
        flex-shrink: 0;
    }

    .power-label {
        color: #fff;
        font-weight: 600;
        font-size: 11px;
        width: 32px;
    }

    .model-label {
        color: #888;
        font-size: 11px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .mode-badge {
        margin-top: 12px;
        display: inline-block;
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
    }

    .mode-badge.gunboat {
        background: #7c3aed;
        color: #fff;
    }

    .mode-badge.press {
        background: #0d9488;
        color: #fff;
    }
</style>
