<script>
    import { selectedGameId, API_BASE } from '$lib/stores.js';

    let threads = [];
    let selectedThread = null;
    let messages = [];
    let pressScores = {};
    let showScores = false;

    const powers = ['England', 'France', 'Germany', 'Italy', 'Austria-Hungary', 'Russia', 'Turkey'];
    const powerColors = {
        'England': '#2563eb',
        'France': '#60a5fa',
        'Germany': '#4b5563',
        'Italy': '#22c55e',
        'Austria': '#ef4444',
        'Austria-Hungary': '#ef4444',
        'Hungary': '#ef4444',
        'Russia': '#a855f7',
        'Turkey': '#f59e0b'
    };

    $: if ($selectedGameId) {
        loadThreads();
        loadPressScores();
        selectedThread = null;
        messages = [];
    }

    async function loadThreads() {
        try {
            const res = await fetch(`${API_BASE}/api/games/${$selectedGameId}/press/threads`);
            threads = await res.json();
        } catch (e) {
            threads = [];
        }
    }

    async function loadPressScores() {
        try {
            const res = await fetch(`${API_BASE}/api/games/${$selectedGameId}/scores`);
            const data = await res.json();
            pressScores = data.press_scores || {};
        } catch (e) {
            pressScores = {};
        }
    }

    function avgScore(arr) {
        if (!arr || arr.length === 0) return '-';
        return (arr.reduce((a, b) => a + b, 0) / arr.length).toFixed(1);
    }

    async function selectThread(thread) {
        selectedThread = thread;
        try {
            const res = await fetch(`${API_BASE}/api/games/${$selectedGameId}/press/${thread.id}`);
            messages = await res.json();
        } catch (e) {
            messages = [];
        }
    }

    function goBack() {
        selectedThread = null;
        messages = [];
    }

    function getPowerColor(sender) {
        for (const [power, color] of Object.entries(powerColors)) {
            if (sender.toLowerCase().includes(power.toLowerCase())) {
                return color;
            }
        }
        return '#6b7280';
    }
</script>

<div class="press-tab">
    {#if !selectedThread}
        <!-- Toggle for press scores -->
        <div class="toggle-row">
            <button class="toggle-btn" class:active={showScores} on:click={() => showScores = !showScores}>
                {showScores ? 'Hide' : 'Show'} Press Evaluation
            </button>
        </div>

        <!-- Press Scores Table -->
        {#if showScores && Object.keys(pressScores).length > 0}
            <div class="scores-table-container">
                <table class="scores-table">
                    <thead>
                        <tr>
                            <th>Power</th>
                            <th>Truthful</th>
                            <th>Coop</th>
                            <th>Deception</th>
                        </tr>
                    </thead>
                    <tbody>
                        {#each powers as power}
                            {@const s = pressScores[power] || {}}
                            {#if s.truthfulness}
                                <tr>
                                    <td class="power-cell" style="--power-color: {powerColors[power]}">
                                        <span class="power-dot"></span>{power.substring(0,3).toUpperCase()}
                                    </td>
                                    <td class="truth">{avgScore(s.truthfulness)}</td>
                                    <td class="coop">{avgScore(s.cooperation)}</td>
                                    <td class="decep">{avgScore(s.deception)}</td>
                                </tr>
                            {/if}
                        {/each}
                    </tbody>
                </table>
            </div>
        {:else if showScores}
            <p class="no-scores">No press evaluation data (requires summaries)</p>
        {/if}

        <!-- Thread list view -->
        <div class="thread-list">
            {#if threads.length === 0}
                <p class="empty">No press messages in this game</p>
            {:else}
                {#each threads as thread}
                    <button class="thread-item" on:click={() => selectThread(thread)}>
                        <div class="thread-powers">
                            {#each thread.powers as power}
                                <span class="power-tag" style="--color: {powerColors[power] || '#6b7280'}">
                                    {power}
                                </span>
                            {/each}
                        </div>
                        <div class="thread-preview">{thread.last_message_preview}</div>
                        <div class="thread-meta">{thread.message_count} messages</div>
                    </button>
                {/each}
            {/if}
        </div>
    {:else}
        <!-- Message view -->
        <div class="message-view">
            <button class="back-btn" on:click={goBack}>
                <span class="arrow">&#8592;</span>
            </button>

            <div class="thread-title">
                {#each selectedThread.powers as power}
                    <span class="power-tag" style="--color: {powerColors[power] || '#6b7280'}">
                        {power}
                    </span>
                {/each}
            </div>

            <div class="messages">
                {#each messages as msg}
                    <div class="message" style="--sender-color: {getPowerColor(msg.sender)}">
                        <div class="message-header">
                            <span class="sender">{msg.sender}</span>
                            <span class="phase">{msg.phase}</span>
                        </div>
                        <div class="message-content">{msg.content}</div>
                    </div>
                {/each}
            </div>
        </div>
    {/if}
</div>

<style>
    .press-tab {
        height: 100%;
        overflow-y: auto;
    }

    .empty {
        color: #888;
        text-align: center;
        padding: 32px;
    }

    .thread-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 16px;
    }

    .thread-item {
        background: #2a2a2a;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 12px;
        text-align: left;
        cursor: pointer;
        transition: background 0.2s;
    }

    .thread-item:hover {
        background: #333;
    }

    .thread-powers {
        display: flex;
        gap: 8px;
        margin-bottom: 8px;
    }

    .power-tag {
        background: var(--color);
        color: #fff;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
    }

    .thread-preview {
        color: #aaa;
        font-size: 13px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    .thread-meta {
        color: #666;
        font-size: 11px;
        margin-top: 4px;
    }

    .message-view {
        padding: 16px;
    }

    .back-btn {
        background: #2a2a2a;
        border: 1px solid #333;
        border-radius: 4px;
        color: #fff;
        padding: 8px 12px;
        cursor: pointer;
        margin-bottom: 16px;
    }

    .back-btn:hover {
        background: #333;
    }

    .thread-title {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid #333;
    }

    .messages {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }

    .message {
        background: #2a2a2a;
        border-left: 3px solid var(--sender-color);
        border-radius: 0 8px 8px 0;
        padding: 12px;
    }

    .message-header {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;
    }

    .sender {
        font-weight: 600;
        color: var(--sender-color);
    }

    .phase {
        font-size: 11px;
        color: #666;
    }

    .message-content {
        color: #ccc;
        font-size: 13px;
        line-height: 1.5;
        white-space: pre-wrap;
    }

    /* Toggle and Scores Table */
    .toggle-row {
        padding: 12px 16px 0;
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
        background: #0d9488;
        border-color: #0d9488;
        color: #fff;
    }

    .scores-table-container {
        margin: 12px 16px;
        background: #1a1a1a;
        border-radius: 6px;
        padding: 12px;
    }

    .scores-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 11px;
        font-family: monospace;
    }

    .scores-table th {
        text-align: center;
        padding: 6px 8px;
        color: #888;
        font-weight: 500;
        border-bottom: 1px solid #333;
    }

    .scores-table td {
        text-align: center;
        padding: 6px 8px;
        color: #ccc;
        border-bottom: 1px solid #222;
    }

    .scores-table .power-cell {
        text-align: left;
        font-weight: 600;
        color: #fff;
    }

    .scores-table .power-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: var(--power-color);
        border-radius: 2px;
        margin-right: 6px;
    }

    .scores-table .truth {
        color: #4ade80;
    }

    .scores-table .coop {
        color: #60a5fa;
    }

    .scores-table .decep {
        color: #f87171;
    }

    .no-scores {
        color: #666;
        font-size: 12px;
        padding: 12px 16px;
        text-align: center;
    }
</style>
