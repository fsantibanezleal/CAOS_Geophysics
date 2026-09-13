import { describe, expect, it } from 'vitest';
import { CASES, makeLiveResult } from '../engine';

describe('browser live lane', () => {
  it('produces finite linked fields for every canonical case', () => {
    for (const item of CASES) {
      const result = makeLiveResult(item.params);
      expect(result.density.every(Number.isFinite)).toBe(true);
      expect(result.gravity.length).toBeGreaterThan(40);
      expect(result.resistivity.length).toBe(result.phase.length);
    }
  });
});
