<script>
    import { selectedGameId, currentPhase, API_BASE } from '$lib/stores.js';

    let orders = [];
    let ordersByPower = {};
    let precision = {};
    let complexityScores = {};
    let errorRates = {};
    let strategicMetrics = {};
    let showPrecision = false;

    const powers = ['England', 'France', 'Germany', 'Italy', 'Austria-Hungary', 'Russia', 'Turkey'];
    const powerColors = {
        'England': '#2563eb',
        'France': '#60a5fa',
        'Germany': '#4b5563',
        'Italy': '#22c55e',
        'Austria': '#ef4444',
        'Austria-Hungary': '#ef4444',
        'Russia': '#a855f7',
        'Turkey': '#f59e0b',
        'Unknown': '#6b7280'
    };

    $: if ($selectedGameId && $currentPhase) {
        loadOrders();
    }

    $: if ($selectedGameId) {
        loadPrecision();
    }

    async function loadOrders() {
        try {
            const res = await fetch(
                `${API_BASE}/api/games/${$selectedGameId}/orders/${$currentPhase.year}/${$currentPhase.season}`
            );
            orders = await res.json();

            // Group by power
            ordersByPower = {};
            for (const order of orders) {
                const power = order.power || 'Unknown';
                if (!ordersByPower[power]) {
                    ordersByPower[power] = [];
                }
                ordersByPower[power].push(order);
            }
        } catch (e) {
            orders = [];
            ordersByPower = {};
        }
    }

    async function loadPrecision() {
        try {
            const res = await fetch(`${API_BASE}/api/games/${$selectedGameId}/scores`);
            const data = await res.json();
            precision = data.precision || {};
            complexityScores = data.complexity_scores || {};
            errorRates = data.error_rates || {};
            strategicMetrics = data.strategic_metrics || {};
        } catch (e) {
            precision = {};
            complexityScores = {};
            errorRates = {};
            strategicMetrics = {};
        }
    }

    function formatOrder(order) {
        let str = `${order.unit} ${order.action}`;
        if (order.destination) {
            str += ` - ${order.destination}`;
        }
        if (order.supporting) {
            str += ` (supporting ${order.supporting})`;
        }
        return str;
    }
</script>

<div class="orders-tab">
    <!-- Toggle for precision table -->
    <div class="toggle-row">
        <button class="toggle-btn" class:active={showPrecision} on:click={() => showPrecision = !showPrecision}>
            {showPrecision ? 'Hide' : 'Show'} Precision Scores
        </button>
    </div>

    <!-- Precision Table -->
    {#if showPrecision && Object.keys(precision).length > 0}
        <div class="precision-table-container">
            <div class="precision-note">Cumulative across all phases</div>
            <table class="precision-table">
                <thead>
                    <tr>
                        <th>Power</th>
                        <th>Invalid</th>
                        <th>Self-Atk</th>
                        <th>Self-Blk</th>
                        <th>Convoys</th>
                        <th>Supp Own</th>
                        <th>Supp Oth</th>
                        <th>Bounces</th>
                    </tr>
                </thead>
                <tbody>
                    {#each powers as power}
                        {@const p = precision[power] || {}}
                        <tr>
                            <td class="power-cell" style="--power-color: {powerColors[power]}">
                                <span class="power-dot"></span>{power.substring(0,3).toUpperCase()}
                            </td>
                            <td class="invalid">{p.invalid_orders || 0}</td>
                            <td class="invalid">{p.self_attacks || 0}</td>
                            <td class="invalid">{p.self_blocks || 0}</td>
                            <td class="good">{p.convoys || 0}</td>
                            <td class="good">{p.support_own || 0}</td>
                            <td class="good">{p.support_other || 0}</td>
                            <td class="bounces">{p.bounces || 0}</td>
                        </tr>
                    {/each}
                </tbody>
            </table>

            <!-- Derived Metrics Table -->
            <div class="precision-note" style="margin-top: 16px;">Derived Metrics</div>
            <table class="precision-table">
                <thead>
                    <tr>
                        <th>Power</th>
                        <th>Complexity</th>
                        <th>Error Rate</th>
                        <th>Peak SC</th>
                        <th>Final SC</th>
                        <th>Survival</th>
                    </tr>
                </thead>
                <tbody>
                    {#each powers as power}
                        {@const complexity = complexityScores[power] || 0}
                        {@const errorRate = errorRates[power] || 0}
                        {@const strat = strategicMetrics[power] || {}}
                        <tr>
                            <td class="power-cell" style="--power-color: {powerColors[power]}">
                                <span class="power-dot"></span>{power.substring(0,3).toUpperCase()}
                            </td>
                            <td class="complexity">{(complexity * 100).toFixed(0)}%</td>
                            <td class="error-rate" class:high-error={errorRate > 0.2}>{(errorRate * 100).toFixed(0)}%</td>
                            <td>{strat.peak_sc_count || 0}</td>
                            <td>{strat.final_sc_count || 0}</td>
                            <td>{strat.survival_years || 0}yr</td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}

    <!-- Orders by Power -->
    {#if Object.keys(ordersByPower).length === 0}
        <p class="empty">No orders for this phase</p>
    {:else}
        {#each Object.entries(ordersByPower) as [power, powerOrders]}
            <div class="power-section">
                <div class="power-header" style="--power-color: {powerColors[power] || '#6b7280'}">
                    <span class="power-marker"></span>
                    <span class="power-name">{power}</span>
                </div>
                <ul class="order-list">
                    {#each powerOrders as order}
                        <li class="order-item">
                            <span class="unit">{order.unit}</span>
                            <span class="action">{order.action}</span>
                            {#if order.destination}
                                <span class="arrow">-</span>
                                <span class="destination">{order.destination}</span>
                            {/if}
                        </li>
                    {/each}
                </ul>
            </div>
        {/each}
    {/if}
</div>

<style>
    .orders-tab {
        padding: 16px;
        height: 100%;
        overflow-y: auto;
    }

    .empty {
        color: #888;
        text-align: center;
        padding: 32px;
    }

    .power-section {
        margin-bottom: 20px;
    }

    .power-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        padding: 4px 0;
        border-bottom: 1px solid #333;
    }

    .power-marker {
        width: 12px;
        height: 12px;
        background: var(--power-color);
        border-radius: 2px;
    }

    .power-name {
        font-weight: 600;
        color: #fff;
        font-size: 14px;
    }

    .order-list {
        list-style: none;
        margin: 0;
        padding: 0;
    }

    .order-item {
        display: flex;
        gap: 6px;
        padding: 4px 0;
        font-size: 13px;
        font-family: monospace;
        color: #ccc;
    }

    .unit {
        color: #fff;
        font-weight: 500;
    }

    .action {
        color: #4af;
    }

    .arrow {
        color: #666;
    }

    .destination {
        color: #8f8;
    }

    /* Toggle and Precision Table */
    .toggle-row {
        margin-bottom: 12px;
    }

    .toggle-btn {
        background: #333;
        border: 1px solid #444;
        color: #888;
        padding: 6px 12px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
    }

    .toggle-btn:hover {
        background: #444;
        color: #fff;
    }

    .toggle-btn.active {
        background: #2563eb;
        border-color: #2563eb;
        color: #fff;
    }

    .precision-table-container {
        margin-bottom: 16px;
        background: #1a1a1a;
        border-radius: 6px;
        padding: 12px;
    }

    .precision-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 11px;
        font-family: monospace;
    }

    .precision-table th {
        text-align: center;
        padding: 6px 4px;
        color: #888;
        font-weight: 500;
        border-bottom: 1px solid #333;
    }

    .precision-table td {
        text-align: center;
        padding: 6px 4px;
        color: #ccc;
        border-bottom: 1px solid #222;
    }

    .precision-table .power-cell {
        text-align: left;
        font-weight: 600;
        color: #fff;
    }

    .precision-table .power-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: var(--power-color);
        border-radius: 2px;
        margin-right: 6px;
    }

    .precision-table .invalid {
        color: #f87171;
    }

    .precision-table .bounces {
        color: #fbbf24;
    }

    .precision-table .good {
        color: #4ade80;
    }

    .precision-table .complexity {
        color: #60a5fa;
    }

    .precision-table .error-rate {
        color: #fbbf24;
    }

    .precision-table .error-rate.high-error {
        color: #f87171;
        font-weight: 600;
    }

    .precision-note {
        font-size: 10px;
        color: #666;
        margin-bottom: 8px;
        text-align: right;
        font-style: italic;
    }
</style>
