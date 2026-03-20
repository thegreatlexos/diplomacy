import { writable, derived } from 'svelte/store';

export const games = writable([]);
export const selectedGameId = writable(null);
export const phases = writable([]);
export const currentPhaseIndex = writable(0);

export const currentPhase = derived(
    [phases, currentPhaseIndex],
    ([$phases, $idx]) => $phases[$idx] || null
);

export const API_BASE = 'http://localhost:8000';
