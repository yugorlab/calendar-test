import { cp, mkdir, copyFile, access } from 'node:fs/promises';
import { constants } from 'node:fs';

const output = new URL('../www/', import.meta.url);
await mkdir(output, { recursive: true });

for (const file of ['index.html', 'events.json']) {
  try {
    await access(new URL(`../${file}`, import.meta.url), constants.R_OK);
    await copyFile(new URL(`../${file}`, import.meta.url), new URL(file, output));
    console.log(`Copied ${file}`);
  } catch {
    if (file === 'index.html') throw new Error('index.html is missing; run this script from the repository root.');
    console.warn(`${file} is not present yet; the app will use its existing fallback data.`);
  }
}

try {
  await cp(new URL('../assets/', import.meta.url), new URL('assets/', output), { recursive: true });
  console.log('Copied assets/');
} catch {
  // The current web calendar does not require a root assets/ directory.
}
