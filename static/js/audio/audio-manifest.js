let manifestPromise = null;

export function getManifest() {
    if (!manifestPromise) {
        manifestPromise = fetch(window.ALCHEMIST_AUDIO.manifestUrl).then((r) => r.json());
    }
    return manifestPromise;
}

export function buildUrl(kind, filename) {
    const encoded = encodeURIComponent(filename);
    switch (kind) {
        case 'music':
            return window.ALCHEMIST_AUDIO.musicBase + encoded;
        case 'passive':
            return window.ALCHEMIST_AUDIO.sfxBase + encoded;
        case 'active':
            return window.ALCHEMIST_AUDIO.sfxActiveBase + encoded;
        default:
            throw new Error(`Unknown audio kind: ${kind}`);
    }
}
