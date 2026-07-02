/**
 * Utility functions for game display
 */

export function formatModelName(modelId: string): string {
  // Clean up model IDs to friendly names
  const modelMap: Record<string, string> = {
    // Anthropic
    'eu.anthropic.claude-opus-4-6-v1': 'Claude Opus 4.6',
    'us.anthropic.claude-opus-4-7': 'Claude Opus 4.7',
    'claude-opus-4.6': 'Claude Opus 4.6',
    'claude-opus-4.7': 'Claude Opus 4.7',
    'eu.anthropic.claude-sonnet-4-6': 'Claude Sonnet 4.6',
    'claude-sonnet-4.6': 'Claude Sonnet 4.6',
    'eu.anthropic.claude-haiku-4-5': 'Claude Haiku 4.5',
    'claude-haiku-4.5': 'Claude Haiku 4.5',

    // OpenAI
    'openai/gpt-5.5': 'GPT-5.5',
    'openai/gpt-4.1-mini': 'GPT-4.1 Mini',
    'gpt-5.5': 'GPT-5.5',
    'gpt-4.1-mini': 'GPT-4.1 Mini',

    // xAI
    'x-ai/grok-4.1-fast': 'Grok 4.1',
    'x-ai/grok-4.3': 'Grok 4.3',
    'grok-4.1-fast': 'Grok 4.1',
    'grok-4.3': 'Grok 4.3',

    // Google
    'google/gemini-3.1-flash-lite-preview': 'Gemini Flash',
    'google/gemini-3.1-pro': 'Gemini Pro',
    'gemini-3.1-flash-lite-preview': 'Gemini Flash',
    'gemini-3.1-pro': 'Gemini Pro',

    // DeepSeek
    'deepseek/deepseek-v4-pro': 'DeepSeek V4',
    'deepseek-v4-pro': 'DeepSeek V4',

    // Mistral
    'mistral/mistral-small': 'Mistral Small',
    'mistral/mistral-large': 'Mistral Large',
    'mistral-small': 'Mistral Small',
    'mistral-large': 'Mistral Large',

    // Meta
    'meta/llama-4-maverick': 'Llama 4',
    'meta/llama-3.1-8b': 'Llama 3.1 8B',
    'llama-4-maverick': 'Llama 4',
    'llama-3.1-8b': 'Llama 3.1 8B',

    // Qwen
    'qwen/qwen3.5-flash': 'Qwen 3.5',
    'qwen3.5-flash': 'Qwen 3.5'
  };

  // Try exact match first
  if (modelMap[modelId]) {
    return modelMap[modelId];
  }

  // Try partial matches
  for (const [key, value] of Object.entries(modelMap)) {
    if (modelId.includes(key) || key.includes(modelId)) {
      return value;
    }
  }

  // Fallback: extract meaningful part
  return modelId
    .replace(/^(eu\.|us\.)?anthropic\./, '')
    .replace(/^(openai|x-ai|google|deepseek|mistral|meta|qwen)\//, '')
    .replace(/-/g, ' ')
    .split(' ')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');
}

export function generateGameTitle(game: any, models?: any[]): string {
  // Generate a descriptive title based on game characteristics
  const winner = game.winner;
  const status = game.status;
  const mode = game.mode;

  // For press games with high deception, use dramatic titles
  if (mode === 'press' && models) {
    const winnerModel = models.find(m => m.power === winner);
    if (winnerModel?.deception_score && winnerModel.deception_score >= 6.0) {
      return `The ${winner} Betrayal`;
    }
  }

  // Status-based titles
  if (status === 'solo') {
    const yearCount = game.end_year - game.start_year + 1;
    if (yearCount <= 12) {
      return `${winner}'s Swift Victory`;
    }
    return `${winner}'s Conquest`;
  }

  if (status === 'stalemate') {
    return `Stalemate: ${winner} Leads`;
  }

  if (status === 'incomplete') {
    return `${winner}'s Campaign (Unfinished)`;
  }

  return `${winner} vs The World`;
}

export function generateGameDescription(game: any, models?: any[]): string {
  const duration = game.end_year - game.start_year + 1;
  const mode = game.mode === 'press' ? 'Full Diplomacy' : 'Gunboat';

  if (game.status === 'solo') {
    return `${duration}-year ${mode.toLowerCase()} game ending in solo victory with ${game.winner_scs} supply centers.`;
  }

  if (game.status === 'stalemate') {
    return `${duration}-year ${mode.toLowerCase()} stalemate with ${game.winner} holding ${game.winner_scs} centers.`;
  }

  return `${duration}-year ${mode.toLowerCase()} game.`;
}

export function getGameHighlight(game: any, models?: any[]): string | null {
  // Return a notable highlight for the game card
  if (game.mode === 'press' && models) {
    const winnerModel = models.find(m => m.power === game.winner);
    if (winnerModel?.deception_score) {
      if (winnerModel.deception_score >= 7.0) {
        return `Master Deceiver (${winnerModel.deception_score.toFixed(1)}/10)`;
      }
      if (winnerModel.truthfulness_score >= 8.0) {
        return `Honest Victor (Truth: ${winnerModel.truthfulness_score.toFixed(1)}/10)`;
      }
    }
  }

  const duration = game.end_year - game.start_year + 1;
  if (duration <= 12 && game.status === 'solo') {
    return `Lightning Fast (${duration} years)`;
  }

  if (game.winner_scs >= 18) {
    return `Dominant Victory (${game.winner_scs} SCs)`;
  }

  return null;
}
