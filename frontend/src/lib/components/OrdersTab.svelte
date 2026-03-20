<script>
    import { selectedGameId, currentPhase, API_BASE } from '$lib/stores.js';

    let orders = [];
    let ordersByPower = {};

    const powerColors = {
        'England': '#2563eb',
        'France': '#60a5fa',
        'Germany': '#4b5563',
        'Italy': '#22c55e',
        'Austria': '#ef4444',
        'Russia': '#a855f7',
        'Turkey': '#f59e0b',
        'Unknown': '#6b7280'
    };

    $: if ($selectedGameId && $currentPhase) {
        loadOrders();
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
</style>
