"""Read Blender's live scene into EditCheck's plain Python data model."""

from pathlib import Path

import bpy

from .rules import Clip, Profile, Snapshot


def _absolute(scene, value):
    return Path(bpy.path.abspath(value, library=scene.library))


def _sources(scene, strip):
    if strip.type == 'MOVIE':
        return [_absolute(scene, strip.filepath)] if strip.filepath else [None]
    if strip.type == 'SOUND':
        if strip.sound is None:
            return [None]
        if strip.sound.packed_file:
            return []
        path = strip.sound.filepath
        return [Path(bpy.path.abspath(path, library=strip.sound.library))] if path else [None]
    if strip.type == 'IMAGE':
        if not strip.directory or not len(strip.elements):
            return [None]
        directory = _absolute(scene, strip.directory)
        return [directory / item.filename for item in strip.elements]
    return []


def capture_scene(scene):
    output = scene.render
    scale = output.resolution_percentage
    profile = Profile(output.resolution_x * scale // 100, output.resolution_y * scale // 100,
                      output.fps / output.fps_base)
    editor = scene.sequence_editor
    if editor is None:
        return Snapshot(scene.name, profile, ())

    clips = []
    for strip in editor.strips_all:
        missing = tuple(path.name if path else '(unset source)' for path in _sources(scene, strip)
                        if path is None or not path.is_file())
        clips.append(Clip(strip.name, strip.channel, int(strip.frame_final_start),
                          int(strip.frame_final_end), strip.mute, missing,
                          bool(getattr(strip, 'use_proxy', False))))
    clips.sort(key=lambda clip: (clip.start, clip.track, clip.name))
    return Snapshot(scene.name, profile, tuple(clips))
