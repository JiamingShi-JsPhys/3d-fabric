'use strict';

/**
 * dsh entry for the directory layout.
 *
 * The bundle itself lives at the repository root (`index.js`, the file
 * `package.json` points at) and registers the skills under `skills/` with the
 * session's skill registry. This file exists because some dsh flows look for a
 * `.dsh-plugin/` directory next to the package manifest; it delegates rather
 * than keeping a second copy that could drift.
 */

const bundle = require('../index.js');

module.exports = {
  name: bundle.name,
  inject: bundle.inject,
  apply: (ctx) => bundle.apply(ctx),
};
