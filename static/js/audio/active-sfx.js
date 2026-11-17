// No call sites exist yet. This module is a seam for future event-to-sound
// wiring once static/audio/sfx/active/ has real clips and a decision is made
// about which in-app events should trigger which sound. The volume/mute
// control in the settings panel is fully wired and persisted even though
// nothing calls this yet. `window.playActiveSfx` is a manual testing hook for
// the browser console, not a real public API.

import { getSettings } from './audio-store.js';
import { getManifest, buildUrl } from './audio-manifest.js';

export async function playActiveSfx(filename) {
    const manifest = await getManifest();
    const pool = (manifest.sfx && manifest.sfx.active) || [];
    if (!pool.includes(filename)) {
        console.warn(`playActiveSfx: "${filename}" not found in active SFX pool.`);
        return;
    }
    const { layers } = getSettings();
    if (layers.sfxActive.muted || layers.sfxActive.volume <= 0) return;
    const clip = new Audio(buildUrl('active', filename));
    clip.volume = layers.sfxActive.volume;
    clip.play().catch(() => {});
}

window.playActiveSfx = playActiveSfx;
