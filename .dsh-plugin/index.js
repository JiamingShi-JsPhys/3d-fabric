'use strict';

/**
 * dsh entry for the directory layout.
 *
 * The bundle itself lives at the repository root (`index.js`, the file
 * `package.json` points at) and registers every `skills/<name>/SKILL.md` with
 * the session's skill registry — in 1.1.0 that is the CAD skill plus the thirty
 * Blender skills. This file exists because some dsh flows look for a
 * `.dsh-plugin/` directory next to the package manifest; it delegates rather
 * than keeping a second copy that could drift.
 */

const bundle = require('../index.js');

module.exports = {
  name: bundle.name,
  inject: bundle.inject,
  apply: (ctx) => bundle.apply(ctx),
};
