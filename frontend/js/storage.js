const LocalData = {
    clearLegacyClinicalData() {
        ['patients', 'situations', 'cards', 'ai_cache'].forEach(function(key) {
            localStorage.removeItem(key);
        });
    },
    getAIProviderState() {
        const defaults = { gigachat: true, yandexgpt: true };
        try {
            const saved = JSON.parse(localStorage.getItem('ai-providers') || '{}');
            return Object.assign({}, defaults, saved || {});
        } catch (error) {
            return Object.assign({}, defaults);
        }
    },
    setAIProviderState(provider, enabled) {
        const state = this.getAIProviderState();
        state[provider] = !!enabled;
        localStorage.setItem('ai-providers', JSON.stringify(state));
        return state;
    },
    getEnabledAIProviders() {
        return Object.entries(this.getAIProviderState())
            .filter(function(entry) { return entry[1]; })
            .map(function(entry) { return entry[0]; });
    },
    getTheme() {
        return localStorage.getItem('app-theme') === 'dark' ? 'dark' : 'light';
    },
    setTheme(theme) {
        const selectedTheme = theme === 'dark' ? 'dark' : 'light';
        localStorage.setItem('app-theme', selectedTheme);
        return selectedTheme;
    }
};