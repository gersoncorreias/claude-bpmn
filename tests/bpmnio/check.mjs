// Parse every .bpmn file under skills/ and examples/ with bpmn-moddle, the parser
// bpmn-js (bpmn.io, Camunda Modeler) uses on import. Any warning, such as an
// unknown element or a reference that does not resolve, fails the check.
//
//   cd tests/bpmnio && npm ci && npm run check
//
// tests/fixtures/ and skills/bpmn-coach/evals/files/ hold deliberately broken diagrams and are skipped.
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { BpmnModdle } from 'bpmn-moddle';

const root = join(fileURLToPath(import.meta.url), '..', '..', '..');
const roots = ['skills', 'examples'].map((d) => join(root, d));
const BROKEN = [join(root, 'skills', 'bpmn-coach', 'evals', 'files')];

function* walk(dir) {
  let entries = [];
  try { entries = readdirSync(dir); } catch { return; }
  for (const name of entries) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) { if (name !== 'node_modules' && !BROKEN.includes(p)) yield* walk(p); }
    else if (name.endsWith('.bpmn')) yield p;
  }
}

const moddle = new BpmnModdle();
let failed = 0;
let count = 0;
for (const dir of roots) {
  for (const file of walk(dir)) {
    count++;
    const rel = relative(root, file).split(sep).join('/');
    try {
      const { warnings } = await moddle.fromXML(readFileSync(file, 'utf8'));
      if (warnings.length) {
        failed++;
        console.log(`FAIL  ${rel}`);
        for (const w of warnings) console.log(`      ${w.message}`);
      } else {
        console.log(`ok    ${rel}`);
      }
    } catch (err) {
      failed++;
      console.log(`FAIL  ${rel}\n      ${err.message}`);
    }
  }
}
console.log(`\n${count - failed}/${count} files parse cleanly with bpmn-moddle`);
process.exit(failed || count === 0 ? 1 : 0);
