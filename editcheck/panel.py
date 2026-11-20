"""Blender panel and local JSON report export."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

import bpy
from bpy.app.handlers import persistent
from bpy.props import BoolProperty, FloatProperty, IntProperty, PointerProperty, StringProperty
from bpy_extras.io_utils import ExportHelper

from .blender_adapter import capture_scene
from .provenance import check_manifest
from .rules import Change, Issue, Profile, Snapshot, check_timeline, describe_clip, timeline_changes


@dataclass(frozen=True)
class Run:
    number: int
    checked_at: str
    snapshot: Snapshot
    expected: Profile | None
    issues: tuple[Issue, ...]
    changes: tuple[Change, ...]


_runs = {}


@persistent
def _clear_runs(_):
    _runs.clear()


class EditCheckSettings(bpy.types.PropertyGroup):
    use_profile: BoolProperty(name='Check scene delivery profile', default=False)
    width: IntProperty(name='Width', default=1920, min=1, max=32768)
    height: IntProperty(name='Height', default=1080, min=1, max=32768)
    fps: FloatProperty(name='Frame rate', default=24.0, min=1.0, max=1000.0, precision=3)
    manifest: StringProperty(name='Research manifest', subtype='FILE_PATH')


class EDITCHECK_OT_scan(bpy.types.Operator):
    bl_idname = 'editcheck.scan'
    bl_label = 'Read Live Timeline'
    bl_description = 'Read the live sequence and check the selected delivery requirements'

    def execute(self, context):
        scene = context.scene
        settings = scene.editcheck_settings
        try:
            snapshot = capture_scene(scene)
        except OSError:
            self.report({'ERROR'}, 'A source path could not be inspected.')
            return {'CANCELLED'}

        expected = Profile(settings.width, settings.height, settings.fps) if settings.use_profile else None
        issues = check_timeline(snapshot, expected)
        if settings.manifest.strip():
            issues += check_manifest(bpy.path.abspath(settings.manifest, library=scene.library))

        key = scene.as_pointer()
        previous = _runs.get(key)
        _runs[key] = Run(
            (previous.number if previous else 0) + 1,
            datetime.now(timezone.utc).isoformat(timespec='seconds'),
            snapshot, expected, issues,
            timeline_changes(previous.snapshot if previous else None, snapshot),
        )
        return {'FINISHED'}


class EDITCHECK_OT_export(bpy.types.Operator, ExportHelper):
    bl_idname = 'editcheck.export_report'
    bl_label = 'Export Last Report'
    filename_ext = '.json'
    filter_glob: StringProperty(default='*.json', options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        return context.scene is not None and context.scene.as_pointer() in _runs

    def execute(self, context):
        run = _runs.get(context.scene.as_pointer())
        if run is None:
            self.report({'ERROR'}, 'Read Live Timeline before exporting a report.')
            return {'CANCELLED'}
        try:
            report = {'schema_version': 1, 'version': '0.1.0', **asdict(run)}
            Path(self.filepath).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        except OSError as error:
            self.report({'ERROR'}, f'Could not write report: {error}')
            return {'CANCELLED'}
        self.report({'INFO'}, 'EditCheck report exported.')
        return {'FINISHED'}


class EDITCHECK_PT_timeline(bpy.types.Panel):
    bl_label = 'EditCheck'
    bl_space_type = 'SEQUENCE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'EditCheck'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.editcheck_settings
        layout.prop(settings, 'use_profile')
        if settings.use_profile:
            row = layout.row(align=True)
            row.prop(settings, 'width')
            row.prop(settings, 'height')
            layout.prop(settings, 'fps')
        layout.prop(settings, 'manifest')
        layout.operator(EDITCHECK_OT_scan.bl_idname, icon='VIEWZOOM')
        run = _runs.get(context.scene.as_pointer())
        if run is None:
            return

        profile = run.snapshot.profile
        layout.label(text=f'Read {run.number} · {len(run.snapshot.clips)} strips')
        layout.label(text=f'{profile.width} × {profile.height} at {profile.fps:g} fps')
        blockers = sum(issue.level == 'error' for issue in run.issues)
        layout.label(text=f'{blockers} blockers · {len(run.issues) - blockers} warnings',
                     icon='ERROR' if blockers else 'CHECKMARK')
        layout.operator(EDITCHECK_OT_export.bl_idname, icon='EXPORT')
        if run.changes:
            layout.label(text='Changed since last read')
            for change in run.changes[:8]:
                box = layout.box()
                box.label(text=change.name)
                box.label(text=f'Before: {describe_clip(change.before)}')
                box.label(text=f'Now: {describe_clip(change.after)}')
            if len(run.changes) > 8:
                layout.label(text='Export the report for the other changes.')
        for issue in run.issues[:8]:
            box = layout.box()
            box.label(text=issue.code)
            box.label(text=issue.subject)
        if run.issues:
            layout.label(text='Export the report for issue details.')
        layout.label(text='Current timeline')
        for clip in run.snapshot.clips[:8]:
            box = layout.box()
            box.label(text=clip.name)
            box.label(text=describe_clip(clip))
        if len(run.snapshot.clips) > 8:
            layout.label(text='Export the report for the other strips.')


_classes = (EditCheckSettings, EDITCHECK_OT_scan, EDITCHECK_OT_export, EDITCHECK_PT_timeline)


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.editcheck_settings = PointerProperty(type=EditCheckSettings)
    bpy.app.handlers.load_post.append(_clear_runs)


def unregister():
    bpy.app.handlers.load_post.remove(_clear_runs)
    _runs.clear()
    del bpy.types.Scene.editcheck_settings
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
