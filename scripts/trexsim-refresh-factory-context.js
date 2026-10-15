#!/usr/bin/env node

const { refresh } = require('./trexsim-factory-context');

const artifacts = refresh();
process.stdout.write(`Refreshed ${Object.keys(artifacts).length} compact factory artifacts.\n`);
