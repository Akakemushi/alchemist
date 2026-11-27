// Any page can declare "this is the active soundscape context right now" by
// dispatching window.dispatchEvent(new CustomEvent('alchemist:soundscape', {
// detail: { key: '<name>' } })) — campaign_play.html does this from its tab
// switcher, using the tab name itself as the key (e.g. 'laboratory'). There is
// no central registry of valid keys: an unrecognized or not-yet-populated key
// just means no passive SFX pool matches it, so nothing plays. Pages that
// never dispatch this event (most of the app) simply have no active
// soundscape, so the passive-ambience layer stays silent there.
//
// The page's own tab-switching script is a plain inline <script> that runs
// synchronously while the document is still parsing, including its very
// first call (activating whichever tab the page loads on). This module,
// though, only loads via <script type="module">, which defers execution
// until after the whole document has parsed — so that very first dispatch
// always happens before this listener exists, and would otherwise be lost.
// To cover that, the tab switcher also writes window.ALCHEMIST_SOUNDSCAPE as
// plain state (not just a one-shot event), which is readable here regardless
// of load order. Later tab switches are still caught live via the event.
let current = window.ALCHEMIST_SOUNDSCAPE || null;

window.addEventListener('alchemist:soundscape', (e) => {
    const key = (e.detail && e.detail.key) || null;
    if (key === current) return;
    current = key;
    window.dispatchEvent(new CustomEvent('alchemist:audio:soundscape-change', { detail: { key } }));
});

export function getCurrentSoundscape() {
    return current;
}
