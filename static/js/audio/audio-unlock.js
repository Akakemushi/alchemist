let unlocked = false;
const queue = [];

function handleFirstGesture() {
    unlocked = true;
    document.removeEventListener('pointerdown', handleFirstGesture, true);
    document.removeEventListener('keydown', handleFirstGesture, true);
    while (queue.length) {
        queue.shift()();
    }
    window.dispatchEvent(new CustomEvent('alchemist:audio:unlocked'));
}

document.addEventListener('pointerdown', handleFirstGesture, true);
document.addEventListener('keydown', handleFirstGesture, true);

export function onUnlock(callback) {
    if (unlocked) {
        Promise.resolve().then(callback);
    } else {
        queue.push(callback);
    }
}
