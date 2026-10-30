import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const run = path.dirname(fileURLToPath(import.meta.url));
const map = JSON.parse(fs.readFileSync(path.join(run, 'copy_map.json'), 'utf8').replace(/^\uFEFF/, ''));
const changes = JSON.parse(fs.readFileSync(path.join(run, 'copy_changes.json'), 'utf8'));
const groups = new Map();
for (const change of changes) {
  const entry = map.entries.find((item) => item.id === change.id);
  if (!entry || entry.protect || entry.text !== change.before) throw Error(`Invalid change: ${change.id}`);
  const edits = groups.get(entry.file) || [];
  edits.push({ ...entry, after: change.after });
  groups.set(entry.file, edits);
}
const outputs = [];
for (const [file, edits] of groups) {
  const filename = path.join(map.root, file);
  let source = fs.readFileSync(filename, 'utf8');
  if (crypto.createHash('sha256').update(source).digest('hex') !== map.hashes[file]) throw Error(`Source changed: ${file}`);
  for (const edit of edits.sort((a, b) => b.start - a.start)) {
    const old = source.slice(edit.start, edit.end);
    let replacement;
    if (edit.kind === 'literal') {
      let text = edit.after;
      if (edit.raw.includes('\n')) {
        const oldLines = edit.raw.split('\n');
        if (oldLines.length !== 2 || !text.includes('. ')) throw Error(`Review line breaks: ${edit.id}`);
        text = text.replace('. ', '.\n' + (oldLines[1].match(/^\s*/) || [''])[0]);
      }
      if (JSON.parse(old) !== edit.raw) throw Error(`Literal mismatch: ${edit.id}`);
      replacement = JSON.stringify(text);
    } else {
      if (old !== edit.raw || /[<>{}]/.test(edit.after)) throw Error(`JSX mismatch: ${edit.id}`);
      replacement = old.match(/^\s*/)[0] + edit.after + old.match(/\s*$/)[0];
    }
    source = source.slice(0, edit.start) + replacement + source.slice(edit.end);
  }
  outputs.push({ filename, source });
}
// Validate every source before writing any changes.
for (const output of outputs) fs.writeFileSync(output.filename, output.source, 'utf8');
console.log(JSON.stringify({ changedFields: changes.length, files: [...groups.keys()] }, null, 2));
