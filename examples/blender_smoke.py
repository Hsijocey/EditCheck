"""Exercise EditCheck inside the actual Blender host using generated local media."""

import argparse
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

import bpy


def run(addon_name, report_path):
    if addon_name == 'editcheck':
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import editcheck
        editcheck.register()
    else:
        bpy.ops.preferences.addon_enable(module=addon_name)
    scene = bpy.context.scene
    scene.name = 'EditCheck Smoke Test'
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.fps = 24
    scene.render.fps_base = 1.0
    settings = scene.editcheck_settings
    settings.use_profile = True
    settings.width, settings.height, settings.fps = 1280, 720, 24
    settings.manifest = str(Path(__file__).resolve().parent / 'research' / 'manifest.json')

    with TemporaryDirectory() as directory:
        asset = Path(directory) / 'sample.png'
        generated = bpy.data.images.new('Temporary test image', width=16, height=16)
        generated.filepath_raw = str(asset)
        generated.file_format = 'PNG'
        generated.save()
        editor = scene.sequence_editor_create()
        strip = editor.strips.new_image('Results', str(asset), 2, 145)
        strip.frame_final_duration = 144

        def scan():
            assert bpy.ops.editcheck.scan() == {'FINISHED'}
            output = Path(directory) / 'report.json'
            assert bpy.ops.editcheck.export_report(filepath=str(output)) == {'FINISHED'}
            return json.loads(output.read_text(encoding='utf-8'))

        first = scan()
        assert first['issues'] == [], first['issues']
        assert first['snapshot']['clips'][0]['start'] == 145
        assert first['snapshot']['clips'][0]['stop'] == 289

        strip.frame_start += 48
        second = scan()
        [change] = second['changes']
        assert change['before']['start'] == 145 and change['before']['stop'] == 289
        assert change['after']['start'] == 193 and change['after']['stop'] == 337

        asset.unlink()
        scene.render.fps = 30
        final = scan()
        assert [item['code'] for item in final['issues']] == ['MISSING_ORIGINAL', 'FRAME_RATE_MISMATCH']
        print('Verified live Blender frames 145–288 → 193–336, then missing source and frame-rate blockers.')
        if report_path:
            payload = {'blender': bpy.app.version_string, 'baseline': first, 'moved': second, 'blocked': final}
            with Path(report_path).open('x', encoding='utf-8') as stream:
                json.dump(payload, stream, ensure_ascii=False, indent=2)
                stream.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--addon', default='editcheck')
    parser.add_argument('--report')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    run(args.addon, args.report)
