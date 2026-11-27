const STORAGE_KEY = 'alchemist:audio:v1';

const DEFAULTS = {
    layers: {
        music:      { volume: 0.5, muted: false },
        sfxPassive: { volume: 0.3, muted: false },
        sfxActive:  { volume: 0.6, muted: false },
    },
    excludedTracks: [],
    playback: null,
};

let cache = null;

function load() {
    if (cache) return cache;
    let parsed = null;
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) parsed = JSON.parse(raw);
    } catch (e) {
        parsed = null;
    }
    cache = {
        layers: {
            music:      { ...DEFAULTS.layers.music,      ...(parsed && parsed.layers && parsed.layers.music) },
            sfxPassive: { ...DEFAULTS.layers.sfxPassive, ...(parsed && parsed.layers && parsed.layers.sfxPassive) },
            sfxActive:  { ...DEFAULTS.layers.sfxActive,  ...(parsed && parsed.layers && parsed.layers.sfxActive) },
        },
        excludedTracks: (parsed && Array.isArray(parsed.excludedTracks)) ? parsed.excludedTracks.slice() : [],
        playback: (parsed && parsed.playback) ? parsed.playback : null,
    };
    return cache;
}

function persist() {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(cache));
    } catch (e) {
        // localStorage unavailable (private mode, quota, etc.) — settings just won't persist
    }
}

function notify(layer) {
    window.dispatchEvent(new CustomEvent('alchemist:audio:change', { detail: { layer } }));
}

export function getSettings() {
    const s = load();
    return {
        layers: {
            music: { ...s.layers.music },
            sfxPassive: { ...s.layers.sfxPassive },
            sfxActive: { ...s.layers.sfxActive },
        },
        excludedTracks: s.excludedTracks.slice(),
    };
}

export function setLayerVolume(layer, volume) {
    const s = load();
    if (!s.layers[layer]) return;
    s.layers[layer].volume = Math.min(1, Math.max(0, volume));
    persist();
    notify(layer);
}

export function setLayerMuted(layer, muted) {
    const s = load();
    if (!s.layers[layer]) return;
    s.layers[layer].muted = !!muted;
    persist();
    notify(layer);
}

export function getExcludedTracks() {
    return load().excludedTracks.slice();
}

export function toggleTrackExcluded(filename) {
    const s = load();
    const idx = s.excludedTracks.indexOf(filename);
    if (idx === -1) {
        s.excludedTracks.push(filename);
    } else {
        s.excludedTracks.splice(idx, 1);
    }
    persist();
    notify('music');
}

export function getPlaybackState() {
    return load().playback;
}

export function savePlaybackState(partial) {
    const s = load();
    s.playback = { ...(s.playback || {}), ...partial };
    persist();
}
