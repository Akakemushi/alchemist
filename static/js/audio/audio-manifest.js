let manifestPromise = null;

export function getManifest() {
    if (!manifestPromise) {
        // Django's dev static serving sends no Cache-Control header at all, so
        // browsers fall back to heuristic caching for this fetch() — which a
        // page hard-refresh doesn't reliably bypass the way it does for a
        // <script src> tag. 'no-cache' forces revalidation every load so a
        // manifest shape change (e.g. the sfx.passive array -> per-soundscape
        // object migration) can never be masked by a stale cached copy.
        manifestPromise = fetch(window.ALCHEMIST_AUDIO.manifestUrl, { cache: 'no-cache' }).then((r) => r.json());
    }
    return manifestPromise;
}

export function buildUrl(kind, filename, opts = {}) {
    const encoded = encodeURIComponent(filename);
    switch (kind) {
        case 'music':
            return window.ALCHEMIST_AUDIO.musicBase + encoded;
        case 'passive':
            return window.ALCHEMIST_AUDIO.sfxPassiveBase + encodeURIComponent(opts.soundscape) + '/' + encoded;
        case 'active':
            return window.ALCHEMIST_AUDIO.sfxActiveBase + encoded;
        default:
            throw new Error(`Unknown audio kind: ${kind}`);
    }
}
