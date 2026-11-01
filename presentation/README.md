# URJA technical presentation

This folder contains a reproducible 10-slide 16:9 PowerPoint presentation, its source generator, and the validated Archify diagrams used in the deck.

## Build the PowerPoint

Requires Node.js 18 or newer.

```powershell
npm ci
npm run build
```

The command writes `urja_presentation.pptx`. The checked-in Archify screenshots in `assets/` are embedded in the deck; all other slide elements are drawn by `generate.js` using PptxGenJS.

## Render and inspect

The delivered PDF and the PowerPoint-rendered slide images are included:

- `urja_presentation.pdf`
- `rendered-final/Slide1.PNG` through `Slide10.PNG`
- `rendered-final/contact-sheet.png`

The PowerPoint COM export used Microsoft PowerPoint on Windows at 1600 × 900 per slide.

## Archify diagrams

Editable candidates are in `diagrams/`:

- `architecture.json` → `architecture.html`
- `processing-workflow.json` → `processing-workflow.html`
- `document-model.json` → `document-model.html`
- `generic-utility-flow.json` → `generic-utility-flow.html`

Each candidate passed Archify showcase validation, delivery, strict artifact check, and automated browser check. Its dark-mode browser capture was cropped into the matching PNG under `assets/` for use in the PowerPoint.

To regenerate a diagram, run the installed Archify CLI sequentially from the project root. Set `ARCHIFY_BIN` to your Archify CLI path if it is not at the default Codex skill location.

```powershell
$archify = $env:ARCHIFY_BIN
if (-not $archify) { $archify = "$HOME\.agents\skills\archify\bin\archify.mjs" }
node $archify finalize architecture presentation/diagrams/architecture.json presentation/diagrams/architecture.html --quality showcase --json
node $archify finalize dataflow presentation/diagrams/processing-workflow.json presentation/diagrams/processing-workflow.html --quality showcase --json
node $archify finalize dataflow presentation/diagrams/document-model.json presentation/diagrams/document-model.html --quality showcase --json
node $archify finalize dataflow presentation/diagrams/generic-utility-flow.json presentation/diagrams/generic-utility-flow.html --quality showcase --json
```

Archify source paths were inspected against the current code, but the workspace has no Git metadata, so the diagram candidates cannot pin a commit revision.

## Scope and accuracy

The example values on slide 7 come from the included four-page electricity-bill fixture. Customer identity and account number are masked. The current semantic adapter specializes in electricity bills; gas and water are shown as future domain extensions. The current API returns a final response and does not expose live stage or page progress.
