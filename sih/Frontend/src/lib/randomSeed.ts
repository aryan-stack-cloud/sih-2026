/** Demo seeds stay clear of the fixed 42–62 training/evaluation worlds. */
export function randomSeed(except?: number): number {
  const random = new Uint32Array(1);
  let seed: number;
  do {
    crypto.getRandomValues(random);
    seed = 1000 + random[0] % 999000;
  } while (seed === except);
  return seed;
}
