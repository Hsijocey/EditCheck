"""Editor-independent preflight rules for a live sequence snapshot."""

from dataclasses import dataclass
from math import isclose


@dataclass(frozen=True)
class Clip:
    name: str
    track: int
    start: int
    stop: int
    muted: bool = False
    missing_sources: tuple[str, ...] = ()
    proxy_enabled: bool = False


@dataclass(frozen=True)
class Profile:
    width: int
    height: int
    fps: float


@dataclass(frozen=True)
class Snapshot:
    scene: str
    profile: Profile
    clips: tuple[Clip, ...]


@dataclass(frozen=True)
class Issue:
    code: str
    subject: str
    detail: str
    level: str = 'error'


@dataclass(frozen=True)
class Change:
    name: str
    before: Clip | None
    after: Clip | None


def describe_clip(clip):
    if clip is None:
        return 'not present'
    return f'Track {clip.track}, frames {clip.start}–{clip.stop - 1}'


def timeline_changes(previous, current):
    if previous is None or previous.scene != current.scene:
        return ()
    before = {clip.name: clip for clip in previous.clips}
    after = {clip.name: clip for clip in current.clips}
    changes = []
    for name in sorted(before.keys() | after.keys()):
        old, new = before.get(name), after.get(name)
        if old is None or new is None or (old.track, old.start, old.stop) != (new.track, new.start, new.stop):
            changes.append(Change(name, old, new))
    return tuple(changes)


def check_timeline(snapshot, expected_profile=None):
    issues = []
    if not snapshot.clips:
        issues.append(Issue('EMPTY_TIMELINE', snapshot.scene, 'The sequence contains no strips.', 'warning'))
    for clip in snapshot.clips:
        if clip.stop <= clip.start:
            issues.append(Issue('INVALID_RANGE', clip.name, 'The strip has no playable frames.'))
        if clip.missing_sources:
            missing = ', '.join(clip.missing_sources[:3])
            tail = f' and {len(clip.missing_sources) - 3} more' if len(clip.missing_sources) > 3 else ''
            proxy = ' Proxy use is enabled.' if clip.proxy_enabled else ''
            issues.append(Issue('MISSING_ORIGINAL', clip.name, f'{describe_clip(clip)}. Missing: {missing}{tail}.{proxy}',
                                'warning' if clip.muted else 'error'))
    if expected_profile is not None:
        actual = snapshot.profile
        if (actual.width, actual.height) != (expected_profile.width, expected_profile.height):
            issues.append(Issue('RESOLUTION_MISMATCH', snapshot.scene,
                                f'Expected {expected_profile.width} × {expected_profile.height}; '
                                f'found {actual.width} × {actual.height} in scene output settings.'))
        if not isclose(actual.fps, expected_profile.fps, rel_tol=0, abs_tol=0.001):
            issues.append(Issue('FRAME_RATE_MISMATCH', snapshot.scene,
                                f'Expected {expected_profile.fps:g} fps; found {actual.fps:g} fps.'))
    return tuple(issues)
