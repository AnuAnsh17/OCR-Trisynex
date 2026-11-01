const pptxgen = require('pptxgenjs');
const fs = require('fs');
const path = require('path');

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'URJA Project';
pptx.subject = 'Technical architecture and project status';
pptx.title = 'URJA — Local-First Document Intelligence for Utility Bills';
pptx.company = 'URJA';
pptx.lang = 'en-IN';
pptx.theme = {
  headFontFace: 'Aptos Display',
  bodyFontFace: 'Aptos',
  lang: 'en-IN'
};
pptx.defineSlideMaster({
  title: 'DARK',
  background: { color: '0B1114' },
  objects: [
    { rect: { x: 0, y: 0, w: 0.055, h: 7.5, line: { color: 'A6F16F', transparency: 100 }, fill: { color: 'A6F16F' } } }
  ]
});
pptx.defineSlideMaster({
  title: 'LIGHT',
  background: { color: 'F3F4EF' },
  objects: [
    { rect: { x: 0, y: 0, w: 0.055, h: 7.5, line: { color: '176B52', transparency: 100 }, fill: { color: '176B52' } } }
  ]
});

const C = {
  bg: '0B1114', bg2: '111A1E', bg3: '182328', paper: 'F3F4EF', white: 'FFFFFF',
  ink: '1E2925', muted: '8D9A93', mutedLight: '59675F', line: '28363A', lineLight: 'D8DED7',
  green: 'A6F16F', greenDark: '176B52', greenSoft: 'E6F0E8', teal: '49D6BD',
  amber: 'E7B85C', amberSoft: 'F5EEDB', red: 'D77368', purple: 'B4A0F7',
  pale: 'DDE5DF', bluegray: 'A9B7B0'
};
const W = 13.333, H = 7.5;
const A = name => path.join(__dirname, 'assets', name);
const D = name => path.join(__dirname, 'diagrams', name);

function txt(slide, value, x, y, w, h, options = {}) {
  const defaults = {
    x, y, w, h, margin: 0, breakLine: false,
    fontFace: options.bold ? 'Aptos Display' : 'Aptos',
    fontSize: 13, color: C.ink, valign: 'mid',
    fit: 'shrink', paraSpaceAfterPt: 0,
    isTextBox: true
  };
  slide.addText(value, { ...defaults, ...options, x, y, w, h });
}
function rect(slide, x, y, w, h, fill, line = fill, radius = false, extra = {}) {
  slide.addShape(radius ? pptx.ShapeType.roundRect : pptx.ShapeType.rect, {
    x, y, w, h, rectRadius: 0.08,
    line: { color: line, width: 0.8 }, fill: { color: fill },
    ...extra
  });
}
function line(slide, x1, y1, x2, y2, color = C.line, width = 1, dash = 'solid', arrow = false) {
  slide.addShape(pptx.ShapeType.line, {
    x: x1, y: y1, w: x2 - x1, h: y2 - y1,
    line: { color, width, dashType: dash, endArrowType: arrow ? 'triangle' : 'none' }
  });
}
function pill(slide, label, x, y, w, fill, color, options = {}) {
  rect(slide, x, y, w, options.h || 0.27, fill, options.line || fill, true);
  txt(slide, label, x + 0.08, y + 0.01, w - 0.16, (options.h || 0.27) - 0.02, {
    fontSize: options.fontSize || 8.5, bold: true, color, align: 'center', charSpacing: 0.3
  });
}
function footer(slide, index, dark = true, label = 'URJA  /  TECHNICAL OVERVIEW') {
  const color = dark ? '728078' : '879087';
  line(slide, 0.67, 7.02, 12.68, 7.02, dark ? '253136' : 'D9DED8', 0.65);
  txt(slide, label, 0.69, 7.1, 4.0, 0.16, { fontSize: 7.5, color, bold: true, charSpacing: 1.0 });
  txt(slide, String(index).padStart(2, '0'), 12.15, 7.08, 0.3, 0.2, { fontSize: 8, color, align: 'right', bold: true });
}
function header(slide, kicker, title, subtitle, dark = true) {
  const accent = dark ? C.green : C.greenDark;
  const primary = dark ? C.white : C.ink;
  const secondary = dark ? C.muted : C.mutedLight;
  txt(slide, kicker.toUpperCase(), 0.68, 0.43, 8.0, 0.2, { fontSize: 8.5, bold: true, color: accent, charSpacing: 1.4 });
  txt(slide, title, 0.68, 0.74, 12.0, 0.47, { fontSize: 25, bold: true, color: primary, charSpacing: -0.4 });
  if (subtitle) txt(slide, subtitle, 0.7, 1.28, 11.9, 0.27, { fontSize: 11.5, color: secondary });
}
function addContainedImage(slide, imagePath, x, y, maxW, maxH, aspect) {
  const w = Math.min(maxW, maxH * aspect);
  const h = w / aspect;
  slide.addImage({ path: imagePath, x: x + (maxW - w) / 2, y: y + (maxH - h) / 2, w, h });
  return { x: x + (maxW - w) / 2, y: y + (maxH - h) / 2, w, h };
}
function bulletDot(slide, x, y, color = C.green, size = 0.07) {
  slide.addShape(pptx.ShapeType.ellipse, { x, y, w: size, h: size, line: { color, transparency: 100 }, fill: { color } });
}
function addInfo(slide, label, value, x, y, w, dark = false, options = {}) {
  const border = dark ? '2A373B' : C.lineLight;
  const surface = dark ? C.bg2 : C.white;
  rect(slide, x, y, w, options.h || 0.66, surface, border, true);
  txt(slide, label.toUpperCase(), x + 0.14, y + 0.09, w - 0.28, 0.15, { fontSize: 7.4, bold: true, color: dark ? C.muted : C.mutedLight, charSpacing: 0.7 });
  txt(slide, value, x + 0.14, y + 0.29, w - 0.28, (options.h || 0.66) - 0.36, {
    fontSize: options.valueSize || 13, bold: options.bold ?? true,
    color: dark ? C.white : C.ink, valign: 'top', breakLine: false
  });
}
function addArrow(slide, x1, y, x2, color = C.greenDark) {
  line(slide, x1, y, x2, y, color, 1.5, 'solid', true);
}

// 01 — A quiet, technical cover: document signals become a structured record.
{
  const s = pptx.addSlide('DARK');
  txt(s, 'URJA', 0.82, 0.64, 2.2, 0.54, { fontSize: 33, bold: true, color: C.white, charSpacing: 3.5 });
  txt(s, 'LOCAL-FIRST  /  DOCUMENT INTELLIGENCE', 0.85, 1.36, 5.6, 0.24, { fontSize: 9, bold: true, color: C.green, charSpacing: 1.5 });
  txt(s, 'From messy utility\ndocuments to structured,\nvalidated data.', 0.82, 1.93, 6.15, 2.15, {
    fontSize: 31, bold: true, color: C.white, breakLine: false, valign: 'mid', charSpacing: -0.6, lineSpacingMultiple: 1.03
  });
  txt(s, 'A document-understanding pipeline built for real Indian utility bills.', 0.86, 4.35, 5.25, 0.5, { fontSize: 14, color: 'B7C2BB', valign: 'top' });
  pill(s, 'PDF + IMAGES', 0.86, 5.23, 1.24, '1B292D', C.pale, { line: '304047' });
  pill(s, 'INDICOCR', 2.22, 5.23, 1.04, '1B292D', C.pale, { line: '304047' });
  pill(s, 'STRUCTURED JSON', 3.38, 5.23, 1.52, '1B292D', C.pale, { line: '304047' });
  txt(s, 'LOCAL PROCESSING  ·  GENERIC DOCUMENT MODEL  ·  DOMAIN-AWARE RESULTS', 0.87, 6.6, 6.5, 0.25, { fontSize: 8.5, color: C.muted, charSpacing: 0.8 });

  // Native vector motif: a page at left, a schema card at right.
  rect(s, 7.38, 1.37, 5.14, 4.93, '111A1E', '28373B', true);
  txt(s, 'DOCUMENT  →  DATA', 7.7, 1.68, 3.7, 0.2, { fontSize: 8.5, bold: true, color: '7E8D85', charSpacing: 1.3 });
  rect(s, 7.76, 2.13, 1.78, 3.37, 'E9ECE5', 'E9ECE5', true);
  rect(s, 7.94, 2.35, 0.66, 0.14, '176B52', '176B52', true);
  txt(s, 'UTILITY BILL', 7.94, 2.62, 1.28, 0.2, { fontSize: 8, bold: true, color: '314139', charSpacing: 0.5 });
  line(s, 7.94, 2.94, 9.33, 2.94, 'B8C1B8', 0.8);
  [3.16, 3.46, 3.77, 4.31, 4.61, 4.92].forEach((yy, i) => {
    rect(s, 7.95, yy, i === 3 ? 1.0 : 1.34, 0.075, i === 4 ? 'C6D1C9' : 'CAD1CA', i === 4 ? 'C6D1C9' : 'CAD1CA', true);
    if ([2, 4].includes(i)) rect(s, 8.84, yy - 0.055, 0.47, 0.16, i === 2 ? 'D8E7D7' : 'E8E0C9', i === 2 ? 'D8E7D7' : 'E8E0C9', true);
  });
  addArrow(s, 9.78, 3.83, 10.28, C.green);
  rect(s, 10.5, 2.13, 1.67, 3.37, '17241F', '385149', true);
  txt(s, '{ }', 10.73, 2.36, 0.56, 0.35, { fontFace: 'Cascadia Code', fontSize: 18, bold: true, color: C.green });
  const schemaLabels = [['provider', C.teal], ['customer', C.green], ['billing', C.amber], ['meter', C.purple], ['evidence', '9DB0A5']];
  schemaLabels.forEach(([label, color], i) => {
    const yy = 2.99 + i * 0.42;
    bulletDot(s, 10.75, yy + 0.04, color, 0.075);
    txt(s, label, 10.9, yy, 0.93, 0.18, { fontFace: 'Cascadia Code', fontSize: 9, color: 'D3DDD5' });
  });
  txt(s, 'Readable output.\nInspectable evidence.', 7.78, 5.73, 4.2, 0.47, { fontSize: 11, color: '91A098' });
  footer(s, 1, true, 'URJA  /  PROJECT OVERVIEW');
}

// 02 — The document is a layout, language and domain problem as much as a text problem.
{
  const s = pptx.addSlide('LIGHT');
  header(s, '01  /  THE INPUT', 'Utility bills are not just text', 'A single page can mix scripts, tables, identifiers, payment cues and provider-specific layouts.', false);
  // Conceptual bill sketch; explicitly schematic, not a scanned source document.
  rect(s, 0.72, 1.82, 4.2, 4.45, C.white, 'D9DED8', true);
  pill(s, 'SCHEMATIC PAGE', 0.96, 2.04, 1.28, 'E8EEE7', C.greenDark, { h: 0.25, fontSize: 7.6 });
  txt(s, 'UTILITY  /  ELECTRICITY', 0.98, 2.46, 2.45, 0.21, { fontSize: 9, bold: true, color: '344239', charSpacing: 0.5 });
  txt(s, 'Account  ••••••2778', 0.98, 2.77, 2.6, 0.2, { fontSize: 9, color: '69756C' });
  line(s, 0.98, 3.09, 4.66, 3.09, 'E3E7E1', 0.8);
  pill(s, 'हिन्दी', 0.98, 3.25, 0.72, 'EEF1ED', '445249', { h: 0.27, fontSize: 8 });
  pill(s, 'मराठी', 1.78, 3.25, 0.75, 'EEF1ED', '445249', { h: 0.27, fontSize: 8 });
  pill(s, 'EN', 2.61, 3.25, 0.55, 'EEF1ED', '445249', { h: 0.27, fontSize: 8 });
  txt(s, 'भुगतान / Payment details', 1.0, 3.69, 3.15, 0.24, { fontSize: 10, bold: true, color: '39463E' });
  // Table-like bill region.
  rect(s, 0.98, 4.03, 3.64, 0.34, 'F0F3EF', 'E2E7E0', true);
  txt(s, 'PERIOD', 1.12, 4.13, 0.85, 0.12, { fontSize: 7.2, bold: true, color: '7A867D' });
  txt(s, 'UNITS', 2.1, 4.13, 0.64, 0.12, { fontSize: 7.2, bold: true, color: '7A867D' });
  txt(s, 'DEMAND', 3.0, 4.13, 0.85, 0.12, { fontSize: 7.2, bold: true, color: '7A867D' });
  [['Aug', '356.12', '2.04 kW'], ['Jul', '581.18', '3.67 kW'], ['Jun', '474.23', '3.23 kW']].forEach((row, i) => {
    const yy = 4.5 + i * 0.34;
    line(s, 1.0, yy + 0.25, 4.6, yy + 0.25, 'EDF0EB', 0.55);
    txt(s, row[0], 1.12, yy, 0.75, 0.18, { fontSize: 8.8, color: '536057' });
    txt(s, row[1], 2.1, yy, 0.72, 0.18, { fontSize: 8.8, color: '536057' });
    txt(s, row[2], 3.0, yy, 0.8, 0.18, { fontSize: 8.8, color: '536057' });
  });
  // A schematic QR / payment zone, not a scannable code.
  rect(s, 3.93, 5.45, 0.5, 0.5, 'F5F6F3', 'CBD3CB', false);
  const qrDots = [[0,0],[1,0],[2,0],[0,1],[2,1],[0,2],[1,2],[2,2],[4,0],[4,1],[3,2],[4,3],[0,4],[1,3],[2,4],[3,4],[4,4],[2,3]];
  qrDots.forEach(([cx, cy]) => rect(s, 3.99 + cx * 0.082, 5.51 + cy * 0.082, 0.055, 0.055, '36443B', '36443B', false));
  txt(s, 'QR / PAY', 3.77, 6.0, 0.85, 0.14, { fontSize: 6.5, bold: true, color: '7A867D', align: 'center' });
  txt(s, 'Representative document anatomy', 0.99, 6.06, 2.6, 0.18, { fontSize: 8, italic: true, color: '879188' });

  const topics = [
    ['01', 'LANGUAGE', 'Hindi, Marathi, English and mixed scripts'],
    ['02', 'STRUCTURE', 'Tables, headings, notices and payment blocks'],
    ['03', 'IDENTITY', 'Account references, customer details and dates'],
    ['04', 'MEASUREMENTS', 'Meter readings, units and usage history']
  ];
  topics.forEach((item, i) => {
    const col = i % 2, row = Math.floor(i / 2), x = 5.45 + col * 3.45, y = 2.02 + row * 1.02;
    txt(s, item[0], x, y, 0.38, 0.22, { fontFace: 'Cascadia Code', fontSize: 9, bold: true, color: C.greenDark });
    txt(s, item[1], x + 0.45, y, 2.6, 0.2, { fontSize: 8, bold: true, color: '78837A', charSpacing: 1.0 });
    txt(s, item[2], x + 0.45, y + 0.31, 2.72, 0.46, { fontSize: 11, color: C.ink, valign: 'top' });
  });
  line(s, 5.45, 4.52, 12.45, 4.52, 'D7DED7', 0.8);
  txt(s, 'The challenge is not reading text.', 5.47, 4.83, 6.6, 0.42, { fontSize: 21, bold: true, color: C.ink, charSpacing: -0.2 });
  txt(s, 'The challenge is understanding the document.', 5.47, 5.32, 6.65, 0.5, { fontSize: 21, bold: true, color: C.greenDark, charSpacing: -0.3 });
  txt(s, 'Layout carries meaning: which value belongs to which account, period, table or payment action.', 5.49, 6.05, 6.4, 0.42, { fontSize: 10.6, color: '68746B', valign: 'top' });
  footer(s, 2, false);
}

// 03 — Contrast text-only OCR with a pipeline that retains document structure.
{
  const s = pptx.addSlide('DARK');
  header(s, '02  /  WHY DOCUMENT UNDERSTANDING', 'Plain OCR can read a value and still lose its meaning', 'Structure links text to rows, fields, pages and evidence.', true);
  const top = 1.82;
  rect(s, 0.72, top, 5.45, 4.54, '111A1E', '2B383D', true);
  pill(s, 'TEXT-ONLY PATH', 0.98, 2.08, 1.42, '27252A', 'D89A91', { line: '503A3C' });
  // Three stacked steps.
  const ly = [2.63, 3.74, 4.84];
  const litems = [
    ['01', 'PDF / PAGE IMAGE', 'visual layout + multilingual text'],
    ['02', 'PLAIN OCR TEXT', 'tokens without table or field links'],
    ['03', 'CONTEXT LOST', 'values become hard to interpret']
  ];
  litems.forEach((item, i) => {
    rect(s, 1.0, ly[i], 4.88, 0.72, i === 2 ? '2B1F20' : '182328', i === 2 ? '674241' : '344248', true);
    txt(s, item[0], 1.17, ly[i] + 0.12, 0.42, 0.18, { fontFace: 'Cascadia Code', fontSize: 9, bold: true, color: i === 2 ? C.red : C.muted });
    txt(s, item[1], 1.75, ly[i] + 0.1, 3.8, 0.19, { fontSize: 9, bold: true, color: i === 2 ? 'E49B91' : C.pale, charSpacing: 0.6 });
    txt(s, item[2], 1.75, ly[i] + 0.38, 3.85, 0.18, { fontSize: 9, color: '96A39B' });
    if (i < 2) line(s, 3.43, ly[i] + 0.73, 3.43, ly[i + 1] - 0.06, '6A7A73', 1, 'solid', true);
  });
  txt(s, 'Text survives; relationships do not.', 1.03, 5.85, 4.6, 0.24, { fontSize: 11, color: 'AAB6AF', italic: true });

  rect(s, 6.48, top, 6.14, 4.54, '111A1E', '2B383D', true);
  pill(s, 'URJA STRUCTURED PATH', 6.75, 2.08, 1.75, '193328', C.green, { line: '2C5846' });
  const sx = 6.82, sw = 5.45;
  const stages = [
    ['DOCUMENT', 'PDF / images'], ['OCR', 'IndicOCR'], ['LAYOUT', 'tables + sections'],
    ['SEMANTICS', 'fields + evidence'], ['CHECKS', 'validation']
  ];
  stages.forEach((step, i) => {
    const yy = 2.66 + i * 0.56;
    bulletDot(s, sx + 0.01, yy + 0.1, i < 2 ? C.teal : i === 4 ? C.amber : C.green, 0.09);
    txt(s, step[0], sx + 0.23, yy, 1.55, 0.2, { fontSize: 9, bold: true, color: C.white, charSpacing: 0.8 });
    txt(s, step[1], sx + 2.0, yy, 2.9, 0.2, { fontSize: 10, color: 'AAB6AF' });
    if (i < stages.length - 1) line(s, sx + 0.055, yy + 0.2, sx + 0.055, yy + 0.5, '43564A', 1);
  });
  rect(s, 6.81, 5.55, 5.45, 0.5, '1D2B25', '355345', true);
  txt(s, 'STRUCTURED JSON', 7.0, 5.7, 1.7, 0.16, { fontSize: 8.5, bold: true, color: C.green, charSpacing: 0.7 });
  txt(s, 'fields  /  tables  /  source evidence', 8.82, 5.69, 3.1, 0.17, { fontSize: 9, color: 'D2DDD5' });
  txt(s, 'Interpretation depends on preserved relationships, not OCR alone.', 6.82, 6.22, 5.5, 0.2, { fontSize: 9.5, color: C.muted });
  footer(s, 3);
}

// 04 — Source-grounded Archify architecture diagram.
{
  const s = pptx.addSlide('DARK');
  header(s, '03  /  SYSTEM ARCHITECTURE', 'A local processing path, with explicit file persistence', 'The API coordinates the current synchronous pass and writes inspectable JSON artifacts.', true);
  addContainedImage(s, A('architecture.png'), 0.68, 1.65, 12.0, 4.78, 1960 / 770);
  pill(s, 'LOCAL APP CONTEXT', 0.76, 6.52, 1.45, '172923', C.green, { line: '2D4A3A' });
  txt(s, 'Filesystem output lives under data/documents/; the current API returns results after processing completes.', 2.38, 6.54, 9.9, 0.18, { fontSize: 9.2, color: 'A7B2AB' });
  footer(s, 4);
}

// 05 — Archify dataflow plus an exact, readable stage strip.
{
  const s = pptx.addSlide('DARK');
  header(s, '04  /  PROCESSING PIPELINE', 'One ordered pass from uploaded files to dashboard data', 'PDFs become page images; the same per-page IndicOCR path handles uploaded images.', true);
  addContainedImage(s, A('processing-workflow.png'), 0.72, 1.58, 11.9, 4.03, 1960 / 685);
  const steps = ['UPLOAD', 'PREPARE', 'OCR', 'RECONSTRUCT', 'EXTRACT', 'VALIDATE', 'SAVE JSON', 'RENDER'];
  const startX = 0.76, gap = 0.095, totalW = 11.86, stepW = (totalW - gap * 7) / 8;
  steps.forEach((step, i) => {
    const x = startX + i * (stepW + gap);
    rect(s, x, 5.84, stepW, 0.46, i === 2 ? '19352C' : '141E22', i === 2 ? '36634D' : '2B393D', true);
    txt(s, `${String(i + 1).padStart(2, '0')}  ${step}`, x + 0.07, 5.97, stepW - 0.14, 0.16, { fontSize: 8, bold: true, color: i === 2 ? C.green : 'C1CCC4', align: 'center', charSpacing: 0.25 });
  });
  txt(s, 'Semantic extraction and deterministic checks currently specialize in electricity bills. Other types retain generic document structure.', 0.8, 6.51, 11.8, 0.22, { fontSize: 9.5, color: C.muted });
  footer(s, 5);
}

// 06 — Semantic record shape with a shared generic layer and scoped adapter.
{
  const s = pptx.addSlide('DARK');
  header(s, '05  /  OUTPUT MODEL', 'A document record carries more than extracted values', 'Generic OCR structure stays available alongside the current electricity semantic view.', true);
  addContainedImage(s, A('document-model.png'), 0.72, 1.48, 11.9, 3.62, 1960 / 685);
  const groups = [
    ['IDENTITY', 'provider · customer · account'],
    ['BILLING', 'dates · amounts · payment'],
    ['USAGE', 'meter · readings · history'],
    ['DOCUMENT', 'tables · notes · notices'],
    ['TRUST', 'validation · field evidence']
  ];
  const x0 = 0.77, chipW = 2.28, chipGap = 0.13;
  groups.forEach((g, i) => {
    const x = x0 + i * (chipW + chipGap);
    rect(s, x, 5.34, chipW, 0.78, '111A1E', '2A383C', true);
    txt(s, g[0], x + 0.14, 5.48, chipW - 0.28, 0.14, { fontSize: 7.4, bold: true, color: C.green, charSpacing: 0.85 });
    txt(s, g[1], x + 0.14, 5.72, chipW - 0.28, 0.17, { fontSize: 8.5, color: 'CFD8D1' });
  });
  txt(s, 'Gas and water semantic adapters are future work; they are not current specialized extractors.', 0.82, 6.44, 11.8, 0.22, { fontSize: 9.5, color: C.muted });
  footer(s, 6);
}

// 07 — Representative test fixture values; identity fields masked.
{
  const s = pptx.addSlide('LIGHT');
  header(s, '06  /  TEST FIXTURE → STRUCTURED RESULT', 'A four-page bill, reduced to reviewable information', 'Representative output from the URJA electricity-bill fixture; customer identifiers are masked.', false);
  // Source document sketch.
  rect(s, 0.72, 1.82, 4.12, 4.72, 'E7EAE4', 'D6DCD5', true);
  rect(s, 0.93, 2.04, 3.7, 4.45, C.white, 'E0E4DE', true);
  pill(s, 'SOURCE DOCUMENT', 1.15, 2.26, 1.42, 'EDF1EC', C.greenDark, { h: 0.25, fontSize: 7.6 });
  txt(s, 'PURVANCHAL VIDYUT', 1.16, 2.69, 2.6, 0.18, { fontSize: 9.2, bold: true, color: '344138', charSpacing: 0.3 });
  txt(s, 'VITARAN NIGAM LTD.', 1.16, 2.91, 2.6, 0.18, { fontSize: 8.6, bold: true, color: '647167' });
  txt(s, 'Account  ••••••2778', 1.16, 3.2, 2.55, 0.16, { fontSize: 8.5, color: '778279' });
  line(s, 1.16, 3.49, 4.4, 3.49, 'E4E8E2', 0.8);
  const billRows = [
    ['CURRENT BILL', '₹2,414.98'], ['PRIOR DUES', '₹0.49'], ['PAYABLE', '₹2,415.00'],
    ['METER READINGS', '10,315.33 → 10,671.28'], ['USAGE', '355.95 kWh']
  ];
  billRows.forEach((row, i) => {
    const yy = 3.68 + i * 0.43;
    txt(s, row[0], 1.17, yy, 1.45, 0.15, { fontSize: 7, bold: true, color: '879188', charSpacing: 0.6 });
    txt(s, row[1], 2.62, yy - 0.01, 1.64, 0.18, { fontSize: 8.7, bold: i === 2, color: '344138', align: 'right' });
    line(s, 1.16, yy + 0.25, 4.4, yy + 0.25, 'EEF0ED', 0.55);
  });
  txt(s, '4 pages  /  11 OCR tables  /  6 usage periods', 1.17, 5.97, 3.05, 0.18, { fontSize: 7.8, color: '7B867D' });
  txt(s, 'TEST FIXTURE · MASKED IDENTITY', 1.17, 6.23, 3.1, 0.15, { fontSize: 7.2, bold: true, color: C.greenDark, charSpacing: 0.85 });

  txt(s, 'EXTRACTED FIELDS', 5.32, 1.92, 3.5, 0.2, { fontSize: 8, bold: true, color: C.greenDark, charSpacing: 1.0 });
  addInfo(s, 'Provider', 'Purvanchal Vidyut Vitaran Nigam Ltd.', 5.3, 2.27, 3.36, false, { h: 0.78, valueSize: 11.5 });
  addInfo(s, 'Customer', 'Anonymized fixture', 8.83, 2.27, 3.78, false, { h: 0.78, valueSize: 12 });
  addInfo(s, 'Account number', '••••••2778', 5.3, 3.16, 2.12, false, { h: 0.68, valueSize: 12 });
  addInfo(s, 'Bill date', '02 Sep 2026', 7.57, 3.16, 2.12, false, { h: 0.68, valueSize: 12 });
  addInfo(s, 'Due date', '17 Sep 2026', 9.84, 3.16, 2.77, false, { h: 0.68, valueSize: 12 });
  addInfo(s, 'Current bill', '₹2,414.98', 5.3, 3.95, 2.12, false, { h: 0.78, valueSize: 15 });
  addInfo(s, 'Payable', '₹2,415.00', 7.57, 3.95, 2.12, false, { h: 0.78, valueSize: 15 });
  addInfo(s, 'Previous dues', '₹0.49', 9.84, 3.95, 2.77, false, { h: 0.78, valueSize: 15 });
  addInfo(s, 'Meter reading', '10,315.33  →  10,671.28', 5.3, 4.85, 3.36, false, { h: 0.78, valueSize: 12.2 });
  addInfo(s, 'Consumption', '355.95 kWh', 8.83, 4.85, 3.78, false, { h: 0.78, valueSize: 14 });
  pill(s, '3 VALIDATION CHECKS PASSED', 5.32, 5.93, 2.43, 'E6F0E8', C.greenDark, { h: 0.29, fontSize: 7.8 });
  txt(s, 'Amounts and meter values shown are fixture outputs, not accuracy benchmarks.', 5.34, 6.36, 6.8, 0.19, { fontSize: 8.5, color: '7A867D' });
  footer(s, 7, false);
}

// 08 — Generic front end, deliberately scoped semantics.
{
  const s = pptx.addSlide('DARK');
  header(s, '07  /  EXTENDING BEYOND ONE BILL LAYOUT', 'One input path. Domain adapters grow by type.', 'Provider-specific layouts do not require provider-specific frontend pages.', true);
  addContainedImage(s, A('generic-utility-flow.png'), 0.72, 1.55, 11.9, 4.15, 1960 / 685);
  rect(s, 0.78, 5.96, 5.7, 0.58, '14211B', '2D4B3A', true);
  txt(s, 'CURRENT', 0.98, 6.15, 0.8, 0.13, { fontSize: 7.6, bold: true, color: C.green, charSpacing: 0.8 });
  txt(s, 'Generic document reconstruction + electricity semantics', 1.93, 6.1, 4.25, 0.22, { fontSize: 9.4, color: C.pale });
  rect(s, 6.72, 5.96, 5.82, 0.58, '211D18', '56452E', true);
  txt(s, 'PLANNED', 6.92, 6.15, 0.83, 0.13, { fontSize: 7.6, bold: true, color: C.amber, charSpacing: 0.8 });
  txt(s, 'Gas / water domain mappings and broader provider coverage', 7.88, 6.1, 4.36, 0.22, { fontSize: 9.2, color: 'DDD4C3' });
  txt(s, 'Unsupported domains can retain generic OCR/document structure; specialized extraction is not implied.', 0.83, 6.7, 11.7, 0.15, { fontSize: 8.4, color: C.muted });
  footer(s, 8);
}

// 09 — Honest processing state next to the focused result surface.
{
  const s = pptx.addSlide('LIGHT');
  header(s, '08  /  DASHBOARD EXPERIENCE', 'A focused workspace, not an operations console', 'The browser shows a quiet indeterminate state while the current API performs its synchronous pass.', false);
  // Left: working state mockup.
  rect(s, 0.72, 1.9, 3.38, 4.45, 'E8ECE6', 'D6DCD5', true);
  txt(s, 'WORKING STATE', 0.99, 2.18, 1.6, 0.16, { fontSize: 7.8, bold: true, color: C.greenDark, charSpacing: 0.9 });
  rect(s, 0.98, 2.57, 2.85, 2.02, C.white, 'DDE3DC', true);
  bulletDot(s, 1.22, 2.9, C.greenDark, 0.12);
  txt(s, 'Processing your document', 1.47, 2.84, 2.0, 0.22, { fontSize: 11.2, bold: true, color: C.ink });
  txt(s, 'Sent to local processor', 1.23, 3.27, 2.2, 0.17, { fontSize: 9, color: '738077' });
  // An indeterminate bar: deliberately no numeric completion percentage.
  s.addShape(pptx.ShapeType.ellipse, { x: 1.23, y: 3.66, w: 0.22, h: 0.22, line: { color: 'CAD6CC', width: 1.4 }, fill: { color: C.white, transparency: 100 } });
  s.addShape(pptx.ShapeType.ellipse, { x: 1.38, y: 3.65, w: 0.065, h: 0.065, line: { color: C.greenDark, transparency: 100 }, fill: { color: C.greenDark } });
  txt(s, 'Processing locally', 1.57, 3.68, 1.85, 0.18, { fontSize: 8.3, color: '879188' });
  line(s, 1.22, 4.31, 3.54, 4.31, 'E6EAE5', 0.7);
  txt(s, 'No live page or stage telemetry is exposed by the API.', 1.22, 4.39, 2.3, 0.33, { fontSize: 8.1, color: '69756D', valign: 'top' });
  txt(s, 'No invented percentages or page counts.', 1.0, 4.88, 2.8, 0.2, { fontSize: 8.4, color: C.greenDark, italic: true });
  pill(s, 'INDETERMINATE BY DESIGN', 1.0, 5.65, 2.03, 'F2F3F0', '68746B', { line: 'DDE2DB', fontSize: 7.4 });

  // Right: a compact result view, not a full browser screenshot.
  rect(s, 4.35, 1.9, 8.25, 4.45, C.white, 'D6DCD5', true);
  rect(s, 4.35, 1.9, 8.25, 0.57, 'FAFBF9', 'FAFBF9', true);
  txt(s, 'DOCUMENT RESULTS', 4.68, 2.1, 2.4, 0.18, { fontSize: 8, bold: true, color: C.greenDark, charSpacing: 0.8 });
  pill(s, 'COMPLETED', 11.14, 2.06, 1.03, 'E6F0E8', C.greenDark, { h: 0.25, fontSize: 7.2 });
  txt(s, 'test_bill.pdf', 4.7, 2.74, 3.0, 0.26, { fontSize: 15, bold: true, color: C.ink });
  txt(s, 'Electricity bill  ·  4 pages', 4.72, 3.06, 3.2, 0.18, { fontSize: 9, color: '78847B' });
  line(s, 4.69, 3.39, 12.21, 3.39, 'E6EAE5', 0.75);
  const mini = [
    ['PROVIDER', 'Purvanchal Vidyut…'], ['ACCOUNT', '••••••2778'], ['CURRENT BILL', '₹2,414.98'],
    ['DUE DATE', '17 Sep 2026'], ['USAGE', '355.95 kWh'], ['METER', '10,315.33 → 10,671.28']
  ];
  mini.forEach((it, i) => {
    const col = i % 3, row = Math.floor(i / 3), x = 4.7 + col * 2.48, y = 3.62 + row * 0.85;
    txt(s, it[0], x, y, 2.25, 0.15, { fontSize: 7, bold: true, color: '89938B', charSpacing: 0.55 });
    txt(s, it[1], x, y + 0.25, 2.25, 0.22, { fontSize: 10, bold: true, color: C.ink });
  });
  rect(s, 4.7, 5.5, 7.52, 0.48, 'F7F9F6', 'E4E8E2', true);
  txt(s, 'DETECTED TABLES', 4.88, 5.66, 1.28, 0.13, { fontSize: 7.2, bold: true, color: '768178', charSpacing: 0.4 });
  ['11 OCR tables', '6 usage periods', 'Validation: passed'].forEach((v, i) => pill(s, v, 6.28 + i * 1.78, 5.61, i === 2 ? 1.58 : 1.5, i === 2 ? 'E6F0E8' : 'ECEFEB', i === 2 ? C.greenDark : '536057', { h: 0.23, fontSize: 7.0 }));
  txt(s, 'Identity values masked for presentation.', 4.72, 6.13, 3.6, 0.15, { fontSize: 7.8, color: '89938B' });
  footer(s, 9, false);
}

// 10 — Clear current capability vs. planned work.
{
  const s = pptx.addSlide('DARK');
  header(s, '09  /  STATUS & NEXT STEPS', 'A working prototype, with a clear expansion path', 'Current scope is useful and inspectable; broader utility coverage still needs domain work.', true);
  rect(s, 0.73, 1.83, 5.82, 4.68, '111A1E', '2B383D', true);
  pill(s, 'IMPLEMENTED NOW', 1.02, 2.12, 1.5, '19352C', C.green, { line: '315844', fontSize: 7.8 });
  const current = [
    'PDF and image ingestion, with ordering and image grouping',
    'Per-page IndicOCR and explicit OCR failure status',
    'Generic page, field, table, section and visual representation',
    'Electricity semantic adapter with candidate evidence',
    'Deterministic validation and local JSON artifacts',
    'Frontend summary, generic tables and technical JSON views'
  ];
  current.forEach((item, i) => {
    const yy = 2.65 + i * 0.53;
    txt(s, '✓', 1.03, yy, 0.22, 0.21, { fontSize: 12, bold: true, color: C.green });
    txt(s, item, 1.37, yy + 0.01, 4.82, 0.31, { fontSize: 10.1, color: 'D8E0D9', valign: 'top' });
  });
  rect(s, 6.79, 1.83, 5.82, 4.68, '171C1D', '3D3930', true);
  pill(s, 'NEXT', 7.08, 2.12, 0.72, '30291D', C.amber, { line: '55442D', fontSize: 7.8 });
  const next = [
    'Semantic adapters for gas, water and more providers',
    'Broader schema review for cross-utility common fields',
    'Persisted document library and lifecycle management',
    'Streaming processing-stage and page progress',
    'More provenance review and conflict-resolution UX',
    'Historical usage analysis and production hardening'
  ];
  next.forEach((item, i) => {
    const yy = 2.65 + i * 0.53;
    txt(s, '→', 7.1, yy, 0.22, 0.21, { fontSize: 12, bold: true, color: C.amber });
    txt(s, item, 7.44, yy + 0.01, 4.82, 0.31, { fontSize: 10.1, color: 'D8D6CF', valign: 'top' });
  });
  txt(s, 'NEXT MILESTONE', 0.89, 6.72, 1.2, 0.14, { fontSize: 7.4, bold: true, color: C.green, charSpacing: 0.8 });
  txt(s, 'Add the next domain adapter without changing the shared intake and rendering contract.', 2.25, 6.68, 9.95, 0.23, { fontSize: 10.3, color: 'BBC6BE' });
  footer(s, 10);
}

const outPath = path.join(__dirname, 'urja_presentation.pptx');
pptx.writeFile({ fileName: outPath }).then(() => {
  console.log(`Wrote ${outPath}`);
  console.log(`Slides: ${pptx._slides.length}`);
}).catch(error => {
  console.error(error);
  process.exitCode = 1;
});
