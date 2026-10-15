// Replays a previously captured synthetic live run; never calls a model.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

export default class SavedResponseProvider {
  constructor(options) {
    const data = JSON.parse(readFileSync(resolve(options.config.report), 'utf8'));
    this.rows = new Map(data.allResults.map((row) => [`${row.category}:${row.number}`, row]));
  }

  id() {
    return 'mama-synthetic-live-run-replay';
  }

  async callApi(prompt) {
    const row = this.rows.get(prompt.trim());
    if (!row) return { error: 'Case missing from saved synthetic run.' };
    return {
      output: JSON.stringify({ answer: row.answer, originalError: row.error, providerCalled: row.providerCalled, seconds: row.seconds }),
      cost: 0,
      metadata: { offlineReplay: true, newModelCalled: false },
    };
  }
}
