import { getSettings, setLayerVolume, setLayerMuted, getExcludedTracks, toggleTrackExcluded } from './audio-store.js';
import { getManifest } from './audio-manifest.js';

const LAYERS = ['music', 'sfxPassive', 'sfxActive'];

function wireTogglePanel() {
    const toggleBtn = document.getElementById('audio-settings-toggle');
    const panel = document.getElementById('audio-settings-panel');
    if (!toggleBtn || !panel) return;

    function close() {
        panel.hidden = true;
        toggleBtn.setAttribute('aria-expanded', 'false');
    }

    function open() {
        panel.hidden = false;
        toggleBtn.setAttribute('aria-expanded', 'true');
    }

    toggleBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        if (panel.hidden) open(); else close();
    });

    document.addEventListener('click', (e) => {
        if (!panel.hidden && !panel.contains(e.target) && e.target !== toggleBtn) close();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !panel.hidden) close();
    });
}

function wireLayerControls() {
    const { layers } = getSettings();
    LAYERS.forEach((layer) => {
        const range = document.getElementById(`audio-vol-${layer}`);
        const mute = document.getElementById(`audio-mute-${layer}`);
        if (range) {
            range.value = layers[layer].volume;
            range.addEventListener('input', () => setLayerVolume(layer, parseFloat(range.value)));
        }
        if (mute) {
            mute.checked = layers[layer].muted;
            mute.addEventListener('change', () => setLayerMuted(layer, mute.checked));
        }
    });
}

async function wireTrackList() {
    const container = document.getElementById('audio-track-list');
    if (!container) return;
    const manifest = await getManifest();
    const excluded = getExcludedTracks();
    (manifest.music || []).forEach((track) => {
        const row = document.createElement('label');
        row.className = 'audio-track-row';
        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.checked = !excluded.includes(track.file);
        checkbox.addEventListener('change', () => toggleTrackExcluded(track.file));
        row.appendChild(checkbox);
        row.appendChild(document.createTextNode(track.label));
        container.appendChild(row);
    });
}

export function init() {
    wireTogglePanel();
    wireLayerControls();
    wireTrackList();
}
