// Deterministic installation fixture. This is not an AI response provider.
export default class OfflineProvider {
  id() {
    return 'mama-local-installation-fixture';
  }

  async callApi(prompt) {
    return {
      output: prompt,
      cost: 0,
      metadata: { offlineFixture: true, modelCalled: false },
    };
  }
}
