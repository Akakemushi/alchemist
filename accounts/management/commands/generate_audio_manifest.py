import json
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Scan static/audio/{music,sfx} and regenerate static/audio/manifest.json. "
        "Passive SFX are organized into 'soundscapes' — one subfolder per context "
        "(e.g. static/audio/sfx/passive/laboratory/) — discovered automatically, so "
        "adding a new soundscape is just a new folder, no code changes. "
        "Re-run after adding, removing, or renaming audio files, and commit the result."
    )

    def handle(self, *args, **options):
        audio_dir = Path(settings.BASE_DIR) / "static" / "audio"
        music_dir = audio_dir / "music"
        sfx_passive_dir = audio_dir / "sfx" / "passive"
        sfx_active_dir = audio_dir / "sfx" / "active"

        music = self._list_mp3(music_dir)
        passive = self._list_soundscapes(sfx_passive_dir)
        active = self._list_mp3(sfx_active_dir)

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "music": [{"file": f, "label": Path(f).stem} for f in music],
            "sfx": {"passive": passive, "active": active},
        }

        manifest_path = audio_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)

        total_passive = sum(len(files) for files in passive.values())
        soundscape_names = ", ".join(sorted(passive)) or "none"
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {manifest_path.relative_to(settings.BASE_DIR)}: "
            f"{len(music)} music tracks, "
            f"{total_passive} passive SFX across soundscape(s) [{soundscape_names}], "
            f"{len(active)} active SFX."
        ))

    @staticmethod
    def _list_mp3(directory):
        if not directory.is_dir():
            return []
        return sorted(
            p.name for p in directory.iterdir()
            if p.is_file() and p.suffix.lower() == ".mp3"
        )

    @classmethod
    def _list_soundscapes(cls, passive_dir):
        if not passive_dir.is_dir():
            return {}
        soundscapes = {}
        for sub in sorted(p for p in passive_dir.iterdir() if p.is_dir()):
            files = cls._list_mp3(sub)
            if files:
                soundscapes[sub.name] = files
        return soundscapes
