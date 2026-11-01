import * as engine from 'minimatch-core';

function unsupported(name) {
  throw new Error(`@city-rating/minimatch-compat: ${name} is not supported by minimatch 11. Update the caller or remove this compatibility bridge; matching has not been skipped.`);
}

export class Minimatch extends engine.Minimatch {
  makeRe() { return unsupported('Minimatch.makeRe()'); }
  static defaults() { return unsupported('Minimatch.defaults()'); }
}

export function minimatch(path, pattern, options) {
  return engine.minimatch(path, pattern, options);
}

export const { sep, GLOBSTAR, filter, braceExpand, match } = engine;
// v11 cannot produce an equivalent legacy RegExp. Fail rather than silently
// changing a rule; defaults would return an unwrapped function, so it also
// remains explicitly unsupported until a caller needs and tests that API.
export const makeRe = () => unsupported('makeRe()');
export const defaults = () => unsupported('defaults()');

Object.assign(minimatch, { minimatch, Minimatch, sep, GLOBSTAR, filter, braceExpand, match, makeRe, defaults });

export default minimatch;
// Node's synchronous require(esm) returns this callable for legacy CJS users.
export { minimatch as 'module.exports' };
