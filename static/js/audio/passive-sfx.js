import { getSettings } from './audio-store.js';
import { getManifest, buildUrl } from './audio-manifest.js';
import { onUnlock } from './audio-unlock.js';

const MIN_DELAY_MS = 5000;
const MAX_DELAY_MS = 15000;

let pool = [];

function randomDelay() {
    return MIN_DELAY_MS + Math.random() * (MAX_DELAY_MS - MIN_DELAY_MS);
}

function playOneIfAllowed() {
    if (!pool.length) return;
    const { layers } = getSettings();
    if (layers.sfxPassive.muted || layers.sfxPassive.volume <= 0) return;
    const file = pool[Math.floor(Math.random() * pool.length)];
    const clip = new Audio(buildUrl('passive', file));
    clip.volume = layers.sfxPassive.volume;
    clip.play().catch(() => {});
}

function scheduleNext() {
    setTimeout(() => {
        playOneIfAllowed();
        scheduleNext();
    }, randomDelay());
}

export async function init() {
    const manifest = await getManifest();
    pool = (manifest.sfx && manifest.sfx.passive) || [];
    if (!pool.length) return;
    onUnlock(scheduleNext);
}
