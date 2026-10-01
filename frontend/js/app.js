document.addEventListener('DOMContentLoaded', async function() {
    await API.checkBackend();
    LocalData.clearLegacyClinicalData();
    SOPEditor.loadList();

    document.querySelectorAll('.ai-provider-toggle').forEach(function(btn) {
        const provider = btn.dataset.aiProvider;
        const enabled = LocalData.getAIProviderState()[provider] !== false;
        btn.classList.toggle('is-on', enabled);
        btn.setAttribute('aria-pressed', enabled ? 'true' : 'false');
        const label = btn.querySelector('.provider-toggle-status');
        if (label) label.textContent = enabled ? 'Вкл' : 'Выкл';

        btn.addEventListener('click', function() {
            const state = LocalData.getAIProviderState();
            const nextValue = !state[provider];
            LocalData.setAIProviderState(provider, nextValue);
            btn.classList.toggle('is-on', nextValue);
            btn.setAttribute('aria-pressed', nextValue ? 'true' : 'false');
            if (label) label.textContent = nextValue ? 'Вкл' : 'Выкл';
        });
    });

    document.querySelectorAll('.tab-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.tab-btn').forEach(function(b) { 
                b.classList.remove('active'); 
            });
            document.querySelectorAll('.tab-content').forEach(function(c) { 
                c.classList.remove('active'); 
            });
            btn.classList.add('active');
            document.getElementById(btn.dataset.tab).classList.add('active');
        });
    });
});
