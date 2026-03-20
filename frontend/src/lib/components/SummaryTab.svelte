<script>
    import { selectedGameId, currentPhase, API_BASE } from '$lib/stores.js';

    let summary = '';

    $: if ($selectedGameId && $currentPhase) {
        loadSummary();
    }

    async function loadSummary() {
        try {
            const res = await fetch(
                `${API_BASE}/api/games/${$selectedGameId}/summary/${$currentPhase.year}/${$currentPhase.season}`
            );
            if (res.ok) {
                const data = await res.json();
                summary = data.content;
            } else {
                summary = '';
            }
        } catch (e) {
            summary = '';
        }
    }
</script>

<div class="summary-tab">
    {#if !summary}
        <p class="empty">No summary for this phase</p>
    {:else}
        <div class="summary-content">
            {@html formatMarkdown(summary)}
        </div>
    {/if}
</div>

<script context="module">
    function formatMarkdown(text) {
        // Basic markdown to HTML conversion
        return text
            // Headers
            .replace(/^### (.+)$/gm, '<h3>$1</h3>')
            .replace(/^## (.+)$/gm, '<h2>$1</h2>')
            .replace(/^# (.+)$/gm, '<h1>$1</h1>')
            // Bold
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            // Italic
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            // Lists
            .replace(/^- (.+)$/gm, '<li>$1</li>')
            .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
            // Code blocks
            .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
            // Inline code
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            // Paragraphs
            .replace(/\n\n/g, '</p><p>')
            // Wrap in paragraph
            .replace(/^(.+)$/gm, (match) => {
                if (match.startsWith('<')) return match;
                return match;
            });
    }
</script>

<style>
    .summary-tab {
        padding: 16px;
        height: 100%;
        overflow-y: auto;
    }

    .empty {
        color: #888;
        text-align: center;
        padding: 32px;
    }

    .summary-content {
        color: #ccc;
        line-height: 1.6;
        font-size: 14px;
    }

    .summary-content :global(h1) {
        font-size: 20px;
        color: #fff;
        margin: 16px 0 8px;
        border-bottom: 1px solid #333;
        padding-bottom: 8px;
    }

    .summary-content :global(h2) {
        font-size: 16px;
        color: #4af;
        margin: 16px 0 8px;
    }

    .summary-content :global(h3) {
        font-size: 14px;
        color: #8f8;
        margin: 12px 0 6px;
    }

    .summary-content :global(strong) {
        color: #fff;
    }

    .summary-content :global(ul) {
        margin: 8px 0;
        padding-left: 20px;
    }

    .summary-content :global(li) {
        margin: 4px 0;
    }

    .summary-content :global(pre) {
        background: #1a1a1a;
        padding: 12px;
        border-radius: 4px;
        overflow-x: auto;
        margin: 12px 0;
    }

    .summary-content :global(code) {
        font-family: monospace;
        background: #333;
        padding: 2px 4px;
        border-radius: 2px;
    }

    .summary-content :global(pre code) {
        background: none;
        padding: 0;
    }
</style>
