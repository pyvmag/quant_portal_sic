(function() {
    function init() {
        if (window.visitorCounterDone) return;
        
        var totalEl = document.getElementById('total-visitors');
        var todayEl = document.getElementById('today-visitors');
        var reviewEl = document.getElementById('review-date');

        if (totalEl && todayEl) {
            window.visitorCounterDone = true;
            
            var todayStr = new Date().toISOString().split('T')[0];
            var visitedKey = 'visited_jalsampada_' + todayStr;
            var isUnique = !localStorage.getItem(visitedKey);
            var cacheBuster = '&t=' + new Date().getTime();

            fetch('/api/method/quant_sic_portal.api.get_visitor_stats?is_unique=' + isUnique + cacheBuster)
            .then(function(r) { return r.json(); })
            .then(function(res) {
                var d = res.message;
                if (d) {
                    totalEl.innerText = 'एकूण दर्शक : ' + d.total_visitors;
                    todayEl.innerText = 'आजचे दर्शक : ' + d.today_visitors;
                    if (reviewEl && d.review_date) {
                        var p = d.review_date.split('-');
                        reviewEl.innerText = 'शेवटचे पुनरावलोकन: ' + p[2] + '-' + p[1] + '-' + p[0];
                    }
                    if (isUnique) localStorage.setItem(visitedKey, 'true');
                }
            })
            .catch(function(e) { console.error('Visitor Counter Error:', e); });
        }
    }

    // Poll as footer might be loaded dynamically
    var interval = setInterval(function() {
        var totalEl = document.getElementById('total-visitors');
        if (totalEl) {
            init();
            clearInterval(interval);
        }
    }, 500);

    // Fallback clear after 10 seconds
    setTimeout(function() { clearInterval(interval); }, 10000);
})();
