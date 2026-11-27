import { getSettings, getExcludedTracks, getPlaybackState, savePlaybackState } from './audio-store.js';
import { getManifest, buildUrl } from './audio-manifest.js';
import { onUnlock } from './audio-unlock.js';

// Seeking (setting audio.currentTime) only works reliably for byte ranges the
// browser has already downloaded, unless the server answers HTTP Range
// requests (206 Partial Content) so the browser can fetch an arbitrary slice
// on demand. `python manage.py runserver` does NOT support Range requests —
// Django's dev-only static file serving ignores the Range header entirely —
// so seeking ahead of what's been progressively downloaded so far will snap
// back to 0 instead of landing where requested. This affects both the resume
// behavior below (pickResumeOrFresh) when the saved position is further into
// the track than a fresh page load has had time to buffer, and the
// AlchemistAudioDebug.skipToEnd() console helper for the same reason.
// In production, this resolves itself as long as whatever actually serves
// /static/ there is Range-aware — a real web server (nginx, Apache) or CDN in
// front of the app typically is by default; Django's own dev server is the
// one exception. No application code change is needed either way; it's a
// property of how the audio bytes get transported, not of this module.
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
let stopped = false;

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

function setNowPlayingLabel(file) {
    const el = document.getElementById('audio-now-playing');
    if (!el) return;
    if (!file) {
        el.textContent = 'Stopped';
        return;
    }
    const track = musicList.find((t) => t.file === file);
    el.textContent = 'Now playing: ' + (track ? track.label : file);
}

function playCurrent(startTime) {
    nextPrepared = false;
    warmedAudio = null;
    const file = trackOrder[position];
    if (!file) {
        stopped = true;
        setNowPlayingLabel(null);
        return;
    }
    stopped = false;
    audio.src = buildUrl('music', file);
    audio.load();
    audio.volume = 0;
    try {
        audio.currentTime = startTime || 0;
    } catch (err) {
        console.warn('[audio] could not seek new track:', err);
    }
    audio.play().catch((err) => console.warn('[audio] play() failed:', err));
    fadeTo(effectiveVolume());
    persist(startTime || 0);
    setNowPlayingLabel(file);
}

function updatePlayPauseButton() {
    const btn = document.getElementById('audio-btn-playpause');
    if (!btn) return;
    btn.textContent = (audio && !audio.paused) ? '⏸' : '▶';
}

function pauseOrPlay() {
    if (!audio || stopped || !audio.src) return;
    if (audio.paused) {
        audio.play().catch((err) => console.warn('[audio] play() failed:', err));
    } else {
        audio.pause();
    }
}

function skipToPrevious() {
    if (!audio || stopped) return;
    if (position > 0) position -= 1;
    playCurrent(0);
}

function skipToNext() {
    if (!audio || stopped) return;
    position += 1;
    ensureQueueLength();
    playCurrent(0);
}

function wireTransportControls() {
    const prevBtn = document.getElementById('audio-btn-prev');
    const playPauseBtn = document.getElementById('audio-btn-playpause');
    const nextBtn = document.getElementById('audio-btn-next');
    if (prevBtn) prevBtn.addEventListener('click', skipToPrevious);
    if (playPauseBtn) playPauseBtn.addEventListener('click', pauseOrPlay);
    if (nextBtn) nextBtn.addEventListener('click', skipToNext);
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
    let manifest;
    try {
        manifest = await getManifest();
    } catch (err) {
        console.error('[audio] failed to load manifest:', err);
        return;
    }
    musicList = manifest.music || [];
    const included = includedFiles();

    audio = document.createElement('audio');
    audio.preload = 'auto';
    audio.volume = 0;
    document.body.appendChild(audio);

    audio.addEventListener('play', updatePlayPauseButton);
    audio.addEventListener('pause', updatePlayPauseButton);
    wireTransportControls();

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
        const nowIncluded = includedFiles();
        if (stopped) {
            // Everything was excluded and playback ran dry — if tracks are
            // available again, start fresh instead of staying silent forever.
            if (nowIncluded.length) {
                trackOrder = shuffle(nowIncluded);
                position = 0;
                playCurrent(0);
            }
            return;
        }
        // Drop newly-excluded tracks from the remaining tail only — never cut
        // the currently-playing track short.
        const tail = trackOrder.slice(position + 1).filter((f) => nowIncluded.includes(f));
        trackOrder = trackOrder.slice(0, position + 1).concat(tail);
    });

    window.addEventListener('beforeunload', () => persist());

    // Manual testing aid: music tracks run several minutes, so waiting for a
    // natural "ended" during testing is slow. In devtools: AlchemistAudioDebug.skipToEnd()
    // Under `runserver` this will often snap back to currentTime 0 instead of
    // actually landing near the end — see the Range-request note at the top
    // of this file. That's the dev server, not a bug in skipToEnd() itself.
    window.AlchemistAudioDebug = {
        getState: () => ({
            file: trackOrder[position],
            position,
            queueLength: trackOrder.length,
            upcoming: trackOrder.slice(position, position + 5),
            includedCount: includedFiles().length,
            stopped,
        }),
        skipToEnd: () => {
            if (!audio || !audio.duration) {
                return { ok: false, reason: 'no track loaded / duration not known yet' };
            }
            const before = { file: trackOrder[position], duration: audio.duration };
            audio.currentTime = Math.max(0, audio.duration - 0.5);
            return { ok: true, before, newCurrentTime: audio.currentTime };
        },
    };

    if (!included.length) {
        stopped = true;
        setNowPlayingLabel(null);
        return;
    }

    const resumed = pickResumeOrFresh(included);
    trackOrder = resumed.trackOrder;
    position = resumed.position;
    const resumeTime = resumed.currentTime;

    onUnlock(() => playCurrent(resumeTime));
}
