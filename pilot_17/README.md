# CampNet pilot test run

This pilot contains **17 posts/images** with author-corrected OCR. Complete the
text-only stage before viewing the full post.

## Open Label Studio

Team LAN URL: **http://192.168.1.17:8081** (host Wi-Fi address checked on
14 October 2026). Everyone must use the same LAN; keep the host computer awake.
If the host's IP changes, check its Wi-Fi IPv4 address with `ipconfig`.

If the server is stopped, run this from the repository root in PowerShell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start_pilot_label_studio.ps1
```

Keep the terminal open. This launcher uses the existing pilot database in
`.pilot-runtime/label-studio`. Its local address is `http://localhost:8081`;
teammates use the LAN URL above. Replace `localhost` in invitation links with
the host's Wi-Fi IP, preserving the rest of the link.

## Project setup (coordinator)

Use existing pilot projects if already created. For initial setup, open Label
Studio, create a pilot account if prompted, then run from the repository root:

```powershell
.\.venv\Scripts\python.exe -m campnet_pilot.labelstudio setup
```

For manual setup, paste the entire XML into the custom labeling setup and import
its matching JSON **once**. Paths below are relative to this folder:

| Stage | UI file | Task import |
| --- | --- | --- |
| A: text only | [config/stage_a_manual.xml](config/stage_a_manual.xml) | [imports/stage_a_manual.json](imports/stage_a_manual.json) |
| B: full post | [config/manual.xml](config/manual.xml) | [imports/manual.json](imports/manual.json) |

For manual Stage B setup, add Local Files source storage pointing to the absolute
`pilot_17/images` folder; save without syncing. Automatic setup handles this.

## Annotation checklist

1. Read the [short codebook](../CampNet_Annotator_Training_Short_Codebook.md).
2. Complete Stage A independently: read caption and corrected image text,
   highlight evidence, and enter the technique, instance number, reason and confidence.
3. Select supported techniques and review status, then submit. If none applies,
   select `No Propaganda Technique` and explain; use `UNRESOLVED` for uncertainty.
4. Have the coordinator export and preserve Stage A before opening Stage B.
   Do not revise Stage A after seeing the image.
5. Complete Stage B with text evidence and relevant image boxes. Link evidence
   for the same claim using the same technique and instance number.
6. Export and validate the results before discussing disagreements. Keep model
   assistance for a separate experiment after independent annotation.

For export commands, validation and troubleshooting, see the
[full pilot workflow](../docs/PILOT_17_WORKFLOW.md).
