/**
 * API client for Diplomacy AI backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface Game {
  id: number;
  game_id: string;
  mode: string;
  platform: string;
  start_year: number;
  end_year: number;
  winner: string;
  winner_model: string;
  winner_scs: number;
  status: string;
}

export interface Model {
  id: number;
  game_id: string;
  power: string;
  model_id: string;
  provider: string;
  tier: string;
  final_rank: number | null;
  final_scs: number;
  deception_score: number | null;
  truthfulness_score: number | null;
  cooperation_score: number | null;
}

export interface SupplyCenterData {
  year: number;
  power: string;
  sc_count: number;
}

export interface PressMessage {
  id: number;
  game_id: string;
  year: number;
  season: string;
  sender: string;
  recipient: string;
  message: string;
}

export interface OverviewStats {
  total_games: number;
  total_providers: number;
  total_years: number;
  total_orders: number;
}

export async function fetchGames(mode?: string, platform?: string): Promise<Game[]> {
  const params = new URLSearchParams();
  if (mode) params.append('mode', mode);
  if (platform) params.append('platform', platform);

  const url = `${API_BASE_URL}/games${params.toString() ? '?' + params.toString() : ''}`;
  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch games: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchGame(gameId: string): Promise<Game> {
  const response = await fetch(`${API_BASE_URL}/games/${gameId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch game: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchGameModels(gameId: string): Promise<Model[]> {
  const response = await fetch(`${API_BASE_URL}/games/${gameId}/models`);

  if (!response.ok) {
    throw new Error(`Failed to fetch models: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchSupplyCenters(gameId: string): Promise<SupplyCenterData[]> {
  const response = await fetch(`${API_BASE_URL}/games/${gameId}/supply-centers`);

  if (!response.ok) {
    throw new Error(`Failed to fetch supply centers: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchPressMessages(gameId: string): Promise<PressMessage[]> {
  const response = await fetch(`${API_BASE_URL}/games/${gameId}/press`);

  if (!response.ok) {
    throw new Error(`Failed to fetch press messages: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchOverviewStats(): Promise<OverviewStats> {
  const response = await fetch(`${API_BASE_URL}/stats/overview`);

  if (!response.ok) {
    throw new Error(`Failed to fetch stats: ${response.statusText}`);
  }

  return response.json();
}

export interface GameFiles {
  visualizations: string[];
  orders: string[];
  press: string[];
}

export async function fetchGameFiles(gameId: string): Promise<GameFiles> {
  const response = await fetch(`${API_BASE_URL}/games/${gameId}/files`);

  if (!response.ok) {
    throw new Error(`Failed to fetch game files: ${response.statusText}`);
  }

  return response.json();
}

export function getVisualizationUrl(gameId: string, filename: string): string {
  return `${API_BASE_URL}/games/${gameId}/visualizations/${filename}`;
}

export interface PowerScore {
  id: number;
  game_id: string;
  power: string;
  total_score: number;
  performance_score: number;
  precision_score: number;
  total_invalid_orders: number;
  total_bounces: number;
  total_supports_own: number;
  total_supports_other: number;
  total_supports_hold: number;
  total_supports_attack: number;
  total_convoys: number;
}

export interface TurnMetric {
  id: number;
  game_id: string;
  year: number;
  season: string;
  power: string;
  invalid_orders: number;
  bounces: number;
  supports_own: number;
  supports_other: number;
  supports_hold: number;
  supports_attack: number;
  convoys: number;
  successful_moves: number;
}

export async function fetchPowerScores(gameId: string): Promise<PowerScore[]> {
  const response = await fetch(`${API_BASE_URL}/games/${gameId}/power-scores`);

  if (!response.ok) {
    throw new Error(`Failed to fetch power scores: ${response.statusText}`);
  }

  return response.json();
}

export async function fetchTurnMetrics(gameId: string, year?: number, season?: string): Promise<TurnMetric[]> {
  let url = `${API_BASE_URL}/games/${gameId}/turn-metrics`;
  const params = new URLSearchParams();
  if (year) params.append('year', year.toString());
  if (season) params.append('season', season);
  if (params.toString()) url += `?${params}`;

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error(`Failed to fetch turn metrics: ${response.statusText}`);
  }

  return response.json();
}

export interface GameEvent {
  id: number;
  game_id: string;
  year: number;
  season: string;
  event_type: string;
  power: string | null;
  description: string;
  metadata: any;
  severity: string;
  created_at: string;
}

export async function fetchGameEvents(gameId: string): Promise<GameEvent[]> {
  const response = await fetch(`${API_BASE_URL}/games/${gameId}/events`);

  if (!response.ok) {
    throw new Error(`Failed to fetch game events: ${response.statusText}`);
  }

  return response.json();
}
