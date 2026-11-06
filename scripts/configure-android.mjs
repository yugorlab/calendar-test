import { readFile, writeFile } from 'node:fs/promises';

const path = new URL('../android/variables.gradle', import.meta.url);
let source = await readFile(path, 'utf8');

function setGradleValue(key, value) {
  const pattern = new RegExp(`(^\\s*${key}\\s*=\\s*)\\d+`, 'm');
  if (!pattern.test(source)) throw new Error(`Could not find ${key} in android/variables.gradle`);
  source = source.replace(pattern, `$1${value}`);
}

setGradleValue('minSdkVersion', 29);
setGradleValue('compileSdkVersion', 36);
setGradleValue('targetSdkVersion', 36);
await writeFile(path, source);
console.log('Android SDK values configured: min 29, compile 36, target 36.');
