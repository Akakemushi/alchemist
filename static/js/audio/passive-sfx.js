import { getSettings } from './audio-store.js';
import { getManifest, buildUrl } from './audio-manifest.js';
import { onUnlock } from './audio-unlock.js';
import { getCurrentSoundscape } from './soundscape.js';

const MIN_DELAY_MS = 5000;
const MAX_DELAY_MS = 15000;

// When entering a soundscape that has clips, don't make the user wait out
// whatever long delay was already in flight from the previous (possibly
// silent) context — fire something fairly soon instead.
const ENTRY_DELAY_MIN_MS = 1000;
const ENTRY_DELAY_MAX_MS = 4000;

let soundscapes = {};
let timerId = null;

function randomDelay(min = MIN_DELAY_MS, max = MAX_DELAY_MS) {
    return min + Math.random() * (max - min);
}

function currentPool() {
    const key = getCurrentSoundscape();
    return (key && soundscapes[key]) || [];
}

function playOneIfAllowed() {
    const key = getCurrentSoundscape();
    const pool = currentPool();
    if (!pool.length) return;
    const { layers } = getSettings();
    if (layers.sfxPassive.muted || layers.sfxPassive.volume <= 0) return;
    const file = pool[Math.floor(Math.random() * pool.length)];
    const clip = new Audio(buildUrl('passive', file, { soundscape: key }));
    clip.volume = layers.sfxPassive.volume;
    clip.play().catch((err) => console.warn('[audio] passive sfx play() failed:', err));
}

function scheduleNext(min, max) {
    if (timerId) clearTimeout(timerId);
    timerId = setTimeout(() => {
        playOneIfAllowed();
        scheduleNext();
    }, randomDelay(min, max));
}

export async function init() {
    const manifest = await getManifest();
    const rawPassive = (manifest.sfx && manifest.sfx.passive) || {};
    if (Array.isArray(rawPassive)) {
        // Legacy/stale manifest shape: sfx.passive used to be a flat filename
        // array before soundscapes existed. soundscapes['laboratory'] on an
        // array is just undefined, which would otherwise fail completely
        // silently — warn instead of leaving passive ambience a mystery.
        console.warn('[audio] manifest.sfx.passive is an array, not a soundscape object — ignoring it.');
        soundscapes = {};
    } else {
        soundscapes = rawPassive;
    }

    // Diagnostic aid: AlchemistSfxDebug.getState() in devtools shows whether
    // a soundscape is currently recognized and whether its pool has clips;
    // playNow() forces an immediate attempt instead of waiting on the timer.
    window.AlchemistSfxDebug = {
        getState: () => ({
            currentSoundscape: getCurrentSoundscape(),
            windowFlag: window.ALCHEMIST_SOUNDSCAPE,
            soundscapeKeys: Object.keys(soundscapes),
            poolLength: currentPool().length,
        }),
        playNow: () => playOneIfAllowed(),
    };

    if (!Object.keys(soundscapes).length) return;

    window.addEventListener('alchemist:audio:soundscape-change', () => {
        if (currentPool().length) scheduleNext(ENTRY_DELAY_MIN_MS, ENTRY_DELAY_MAX_MS);
    });

    onUnlock(() => scheduleNext());
}
