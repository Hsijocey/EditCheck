# EditCheck

EditCheck is a Blender Video Sequence Editor add-on for checking the timeline and delivery settings of a research video. It also verifies that a research figure, its generator, and its inputs match the files recorded when the figure was built.

## Install and run

1. Use Blender 4.5 LTS. The 0.1.0 package was tested on Windows with Blender 4.5.16.
2. In **Edit → Preferences → Get Extensions**, open the menu in the upper right, choose **Install from Disk**, and select `EditCheck-0.1.0.zip`. Enable **EditCheck** in **Add-ons** if needed.
3. Open a project containing a timeline in the **Video Sequencer**. Press **N** to open the sidebar and select the **EditCheck** tab.
4. Click **Read Live Timeline**. Optionally enable **Check scene delivery profile** and enter the required resolution and frame rate. To verify research figures, select a research manifest in the same panel.
5. Move or trim a strip and click **Read Live Timeline** again to see the before and after ranges. Use **Export Last Report** to save the full scan as a JSON file in a location you choose.

The scan operates on the current Blender scene and keeps the previous scan in memory. It uses local files throughout. Panels show up to eight entries per section, and the JSON report contains all entries.

## Rules

| Check | Inputs | Report |
| --- | --- | --- |
| Timeline changes | Track and frame bounds read from Blender on each click | Before and after ranges for moved, trimmed, added, and removed strips. The comparison keys on strip name within the current scene, so renames appear as a removal and an addition. |
| Original media | Paths for movie, sound, and image strips, including strips inside metas | Missing originals are blockers. A muted strip's missing original is a warning. An enabled proxy is noted separately. Packed sounds are treated as present. |
| Delivery profile | Scene render dimensions after percentage scaling and scene FPS divided by FPS base | Resolution and frame-rate mismatches. FPS tolerance is 0.001 fps. This check describes the scene settings. File-level verification of a rendered export is a future feature. |
| Figure provenance | SHA-256 fingerprints for the generated figure, generator script, and inputs | A changed, missing, or unreadable file is reported by role. Run the generator explicitly after reviewing the changes to refresh the figure and its manifest. |

Blender's end frame is exclusive. The panel shows inclusive frame ranges. The JSON snapshots keep `start` inclusive and `stop` exclusive.

## Architecture

- [`editcheck/blender_adapter.py`](editcheck/blender_adapter.py) reads `scene.sequence_editor.strips_all` through Blender's Python API and checks original media paths. It builds a snapshot of strip bounds, track numbers, and scene output settings.
- [`editcheck/rules.py`](editcheck/rules.py) compares two snapshots and checks delivery requirements using plain Python data classes.
- [`editcheck/provenance.py`](editcheck/provenance.py) validates the figure manifest and streams each selected file through SHA-256. It resolves paths inside the manifest directory and reports manifest errors separately from file changes.
- [`editcheck/panel.py`](editcheck/panel.py) runs the checks, shows the current snapshot and changes, and exports the report on request. The scan leaves the timeline and source media untouched.

The live integration in this release is Blender VSE. The research-manifest checker is also available without Blender. Premiere integration remains a future adapter.

## Reproduce the checks locally

Run the research example and unit tests from the checkout root using Python 3.10 or later. The example uses synthetic data, and the generator produces `figure.svg` and `manifest.json` from the CSV locally.

```sh
python -m editcheck examples/research/manifest.json
python -m unittest discover -s tests -v
```

To reproduce the stale-file check, work on a copy of the example directory. Change the third measurement from `20` to `26` and run `python -m editcheck <copy>/manifest.json`. The CLI reports `RESEARCH_FILE_CHANGED` for the input. To regenerate the tracked example in the checkout, run `python -m examples.research.generate_figure`.

The manifest is a JSON object with `schema_version: 1` and a `figures` array. Each entry contains `name`, `artifact`, `script`, and an `inputs` array. `artifact`, `script`, and each input contain `path` relative to the manifest and a `sha256` string. See the [working sample](examples/research/manifest.json).

To exercise the actual Blender integration in a disposably generated scene, use the included smoke test. Replace `blender` with the Blender executable's path if required.

```sh
blender --background --factory-startup --python-exit-code 9 --python examples/blender_smoke.py
```

The test adds a real image strip, reads it at frames 145–288, moves it by 48 frames, and verifies the live readback at 193–336. It then removes its generated test media, changes the scene to 30 fps, and checks for both blockers. The test also exercises JSON report export and verifies the checked-in research manifest in Blender.

The [Windows verification report](verification/blender-4.5.16-windows.json) records those three reads from the packaged extension installed into a fresh Blender 4.5.16 profile. The source strip uses a generated image and the research example uses synthetic measurements.

## Build a release

```sh
blender --command extension build --source-dir editcheck --output-filepath EditCheck-0.1.0.zip
blender --command extension validate EditCheck-0.1.0.zip
```

Only the `editcheck/` extension source is packaged. The Python example, fixtures, and host smoke test stay in the source repository.

The SHA-256 digest of the Windows-tested ZIP is `c096b551e2e0c0994acd1b5b67db5ad1bf7399a7bca3909c44f59420c6cd72f5`.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
