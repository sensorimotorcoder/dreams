# Google Sheets Add-on (Apps Script)

## Required Headers

Ensure your sheet contains the following columns before running the add-on:

- `new_id`
- `morning_recall_1`
- Output columns you want the engine to populate, e.g. `sensorimotor`, `reason_sensorimotor`, `conf`,
  `Valence`, `Setting`, `Presence`, `Agent`, `Visual`, `Auditory`, `Tactile`, `Olfactory`, `Gustatory`,
  `Body State`, `Motor`, `Object`, `engine_version`, `preset_version`, `last_coded_at`, `review_status`,
  `review_notes`

## Apps Script Code

1. Open your Google Sheet and navigate to **Extensions → Apps Script**.
2. Replace the contents with the script below and update `API_BASE` to point at your deployed API. Optionally set
   `PRESET` to a preset key returned by `GET /presets`.

```javascript
const API_BASE = 'https://YOUR-DEPLOYED-ENGINE'; // e.g., https://textcoder.onrender.com
const PRESET = 'dreams-sensorimotor@0.4.0';       // or '' to use the ad-hoc config

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('Coder')
    .addItem('Code selected rows', 'codeSelectedRows')
    .addItem('Code all uncoded', 'codeAllUncoded')
    .addItem('Propose lexicon extensions', 'openLexiconDialog')
    .addToUi();
}

function codeSelectedRows() {
  const sh = SpreadsheetApp.getActiveSheet();
  const range = sh.getActiveRange();
  const hdr = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
  const idxId = hdr.indexOf('new_id');
  const idxText = hdr.indexOf('morning_recall_1');
  if (idxId < 0 || idxText < 0) throw new Error('Missing headers new_id or morning_recall_1');

  const rows = [];
  range.getValues().forEach((row, offset) => {
    const rowNumber = range.getRow() + offset;
    if (rowNumber === 1) return; // skip header
    rows.push({ row: rowNumber, new_id: row[idxId], text: row[idxText] });
  });
  if (!rows.length) return;

  const res = UrlFetchApp.fetch(`${API_BASE}/code`, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({ rows, preset: PRESET })
  });
  const out = JSON.parse(res.getContentText());
  writeResults_(sh, hdr, out.results);
}

function codeAllUncoded() {
  const sh = SpreadsheetApp.getActiveSheet();
  const hdr = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
  const idxId = hdr.indexOf('new_id');
  const idxText = hdr.indexOf('morning_recall_1');
  const idxVersion = hdr.indexOf('engine_version');
  if (idxId < 0 || idxText < 0 || idxVersion < 0) throw new Error('Missing headers');

  const values = sh.getRange(2, 1, sh.getLastRow() - 1, sh.getLastColumn()).getValues();
  const rows = [];
  values.forEach((row, offset) => {
    if (!row[idxVersion]) {
      rows.push({ row: offset + 2, new_id: row[idxId], text: row[idxText] });
    }
  });
  if (!rows.length) return;

  const res = UrlFetchApp.fetch(`${API_BASE}/code`, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({ rows, preset: PRESET })
  });
  const out = JSON.parse(res.getContentText());
  writeResults_(sh, hdr, out.results);
}

function writeResults_(sh, hdr, results) {
  const column = name => hdr.indexOf(name) + 1;
  const now = new Date().toISOString();
  results.forEach(result => {
    const row = result.row;
    const coded = result.coded;
    const set = (name, value) => {
      const colIndex = column(name);
      if (colIndex > 0) sh.getRange(row, colIndex).setValue(value);
    };
    set('sensorimotor', coded.sensorimotor || 0);
    set('reason_sensorimotor', coded.reason_sensorimotor || '');
    set('conf', coded.conf || 1);
    set('Valence', coded.valence_label || '');
    set('Setting', (coded.setting_hits || '').replace(/,/g, '|'));
    set('Presence', coded.presence_label || '');
    set('Agent', coded.agent_supernatural ? 1 : 0);
    set('Visual', coded.reason_visual || '');
    set('Auditory', coded.reason_auditory || '');
    set('Tactile', coded.reason_tactile || '');
    set('Olfactory', coded.reason_olfactory || '');
    set('Gustatory', coded.reason_gustatory || '');
    set('Body State', coded.sensorimotor ? 'embodied' : '');
    set('Motor', coded.reason_motor || '');
    set('Object', coded.reason_object || '');
    set('engine_version', result.code_version);
    set('preset_version', result.preset_version);
    set('last_coded_at', now);
    if (column('review_status') > 0 && !sh.getRange(row, column('review_status')).getValue()) {
      set('review_status', coded.conf === 1 ? 'needs_review' : 'accepted');
    }
  });
}

function openLexiconDialog() {
  const html = HtmlService.createHtmlOutput('<p>Use the API or CLI to post to /extend_lexicon for detailed lexicon proposals.</p>')
    .setWidth(420)
    .setHeight(160);
  SpreadsheetApp.getUi().showModalDialog(html, 'Lexicon Builder');
}
```
