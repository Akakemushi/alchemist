import { getSettings, getExcludedTracks, getPlaybackState, savePlaybackState } from './audio-store.js';
import { getManifest, buildUrl } from './audio-manifest.js';
import { onUnlock } from './audio-unlock.js';

const RESUME_MAX_AGE_MS = 2 * 60 * 60 * 1000;
const PRELOAD_LEAD_SECONDS = 5;
const FADE_MS = 800;

let audio = null;
let musicList = [];
let trackOrder = [];
let position = 0;
let nextPrepared = false;
let warmedAudio = null;
let fadeIntervalId = null;

function shuffle(arr) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
}

function fadeTo(target, ms = FADE_MS) {
    if (fadeIntervalId) clearInterval(fadeIntervalId);
    const steps = 20;
    const stepTime = ms / steps;
    const start = audio.volume;
    let i = 0;
    fadeIntervalId = setInterval(() => {
        i++;
        audio.volume = start + (target - start) * (i / steps);
        if (i >= steps) {
            audio.volume = target;
            clearInterval(fadeIntervalId);
            fadeIntervalId = null;
        }
    }, stepTime);
}

function effectiveVolume() {
    const { layers } = getSettings();
    return layers.music.muted ? 0 : layers.music.volume;
}

function includedFiles() {
    const excluded = getExcludedTracks();
    return musicList.filter((t) => !excluded.includes(t.file)).map((t) => t.file);
}

function pickResumeOrFresh(included) {
    const saved = getPlaybackState();
    if (
        saved &&
        Array.isArray(saved.trackOrder) &&
        saved.savedAt &&
        (Date.now() - saved.savedAt) < RESUME_MAX_AGE_MS &&
        saved.trackOrder.length &&
        saved.trackOrder.every((f) => included.includes(f))
    ) {
        return {
            trackOrder: saved.trackOrder,
            position: saved.position || 0,
            currentTime: saved.currentTime || 0,
        };
    }
    return { trackOrder: shuffle(included), position: 0, currentTime: 0 };
}

// Keep at least one unplayed track queued past the current position, growing
// the (shuffled) order rather than wrapping an index — avoids ever needing to
// "guess" a reshuffle for preload purposes and then redo it for real playback.
function ensureQueueLength() {
    if (trackOrder.length - position < 2) {
        trackOrder = trackOrder.concat(shuffle(includedFiles()));
    }
}

function persist(currentTime) {
    savePlaybackState({
        trackOrder,
        position,
        currentTime: currentTime != null ? currentTime : (audio ? audio.currentTime : 0),
        savedAt: Date.now(),
    });
}

function playCurrent(startTime) {
    nextPrepared = false;
    warmedAudio = null;
    const file = trackOrder[position];
    if (!file) return;
    audio.src = buildUrl('music', file);
    audio.volume = 0;
    audio.currentTime = startTime || 0;
    audio.play().catch(() => {});
    fadeTo(effectiveVolume());
    persist(startTime || 0);
}

function prepareNext() {
    nextPrepared = true;
    ensureQueueLength();
    const nextFile = trackOrder[position + 1];
    if (!nextFile) return;
    // Warming the browser's HTTP cache for the next file, so the real swap on
    // "ended" starts near-instantly instead of waiting on a fresh download.
    warmedAudio = new Audio(buildUrl('music', nextFile));
    warmedAudio.preload = 'auto';
}

export async function init() {
    const manifest = await getManifest();
    musicList = manifest.music || [];
    const included = includedFiles();
    if (!included.length) return;

    const resumed = pickResumeOrFresh(included);
    trackOrder = resumed.trackOrder;
    position = resumed.position;
    const resumeTime = resumed.currentTime;

    audio = document.createElement('audio');
    audio.preload = 'auto';
    audio.volume = 0;
    document.body.appendChild(audio);

    audio.addEventListener('timeupdate', () => {
        if (!nextPrepared && audio.duration && (audio.duration - audio.currentTime) < PRELOAD_LEAD_SECONDS) {
            prepareNext();
        }
    });

    audio.addEventListener('ended', () => {
        position += 1;
        ensureQueueLength();
        playCurrent(0);
    });

    window.addEventListener('alchemist:audio:change', (e) => {
        if (e.detail.layer !== 'music') return;
        audio.volume = effectiveVolume();
        // Drop newly-excluded tracks from the remaining tail only — never cut
        // the currently-playing track short.
        const nowIncluded = includedFiles();
        const tail = trackOrder.slice(position + 1).filter((f) => nowIncluded.includes(f));
        trackOrder = trackOrder.slice(0, position + 1).concat(tail);
    });

    window.addEventListener('beforeunload', () => persist());

    onUnlock(() => playCurrent(resumeTime));
}
