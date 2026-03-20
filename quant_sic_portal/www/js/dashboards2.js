
document.addEventListener('DOMContentLoaded', () => {
    const sheetURL = "https://docs.google.com/spreadsheets/d/1uZMDUujtlQr_G5E720P0upyQJ2Pfwiu_m8DIorZZyvA/gviz/tq?tqx=out:json";

    const fetchData = async (url) => {
        const response = await fetch(url);
        const text = await response.text();
        const json = JSON.parse(text.substr(47).slice(0, -2));
        return json.table.rows.map(r => {
            let rowObj = {};
            r.c.forEach((cell, i) => {
                rowObj[`col${i}`] = cell && cell.v != null ? cell.v : null;
            });
            return rowObj;
        });
    };

    const mapSheetData = (data) => {
        return data.map(r => ({
            'अ.क्र.': r.col0,
            'जिल्हा': r.col1,
            'तालुका': r.col2,
            'धरणाचे नाव': r.col3,
            'प्रकल्प प्रकार': r.col4,
            'total_storage': r.col5 != null ? Number(r.col5) : 0,
            'percentage': r.col6 != null ? Number(r.col6) : 0
        }));
    };

    const displayKPIs = (data) => {
        document.getElementById('total-dams').innerText = data.length;
        const avg = data.reduce((sum, d) => sum + d.percentage, 0) / data.length;
        document.getElementById('avg-storage').innerText = `${avg.toFixed(1)}%`;
        const above90 = data.filter(d => d.percentage >= 90).length;
        document.getElementById('dams-above-90').innerText = above90;
    };

    const createStorageByDistrictChart = (data) => {
        const ctx = document.getElementById('storageByDistrictChart').getContext('2d');
        const districtData = {};
        data.forEach(d => {
            const district = d.जिल्हा || 'Unknown';
            districtData[district] = (districtData[district] || 0) + d.total_storage;
        });
        new Chart(ctx, {
            type: 'doughnut',
            data: { labels: Object.keys(districtData), datasets: [{ data: Object.values(districtData), backgroundColor: ['#007bff','#28a745','#ffc107','#dc3545','#17a2b8'] }] },
            options: { responsive:true, maintainAspectRatio:false, plugins:{ title:{ display:true, text:'Total Water Storage by District' } } }
        });
    };

    const createStorageByTypeChart = (data) => {
        const ctx = document.getElementById('storageByTypeChart').getContext('2d');
        const typeData = {};
        data.forEach(d => {
            const type = d['प्रकल्प प्रकार'] || 'Unknown';
            typeData[type] = (typeData[type] || 0) + d.total_storage;
        });
        new Chart(ctx, {
            type: 'bar',
            data: { labels: Object.keys(typeData), datasets: [{ label:'Total Storage (MCFT)', data: Object.values(typeData), backgroundColor:'#28a745' }] },
            options: { responsive:true, maintainAspectRatio:false, plugins:{ title:{ display:true, text:'Total Storage by Project Type' } }, scales:{ y:{ beginAtZero:true } } }
        });
    };

    const createTopDamsChart = (data) => {
        const ctx = document.getElementById('topDamsChart').getContext('2d');
        const top10 = data.sort((a,b) => b.total_storage - a.total_storage).slice(0,10);
        new Chart(ctx, {
            type:'bar',
            data: { labels: top10.map(d=>d['धरणाचे नाव']), datasets:[{ label:'Total Storage (MCFT)', data: top10.map(d=>d.total_storage), backgroundColor:'#ffc107' }] },
            options:{ indexAxis:'y', responsive:true, maintainAspectRatio:false, plugins:{ title:{ display:true, text:'Top 10 Dams by Total Storage Capacity' } }, scales:{ x:{ beginAtZero:true } } }
        });
    };

    const createDamsByTalukaChart = (data) => {
        const ctx = document.getElementById('damsByTalukaChart').getContext('2d');
        const talukaData = {};
        data.forEach(d => {
            const t = d.तालुका || 'Unknown';
            talukaData[t] = (talukaData[t] || 0) + 1;
        });
        new Chart(ctx, {
            type:'bar',
            data: { labels:Object.keys(talukaData), datasets:[{ label:'Number of Dams', data:Object.values(talukaData), backgroundColor:'#dc3545' }] },
            options:{ indexAxis:'y', responsive:true, maintainAspectRatio:false, plugins:{ title:{ display:true, text:'Number of Dams per Taluka' } }, scales:{ x:{ beginAtZero:true, ticks:{ stepSize:1 } } } }
        });
    };

    const buildDashboard = async () => {
        try {
            const rawData = await fetchData(sheetURL);
            const data = mapSheetData(rawData);
            displayKPIs(data);
            createStorageByDistrictChart(data);
            createStorageByTypeChart(data);
            createTopDamsChart(data);
            createDamsByTalukaChart(data);
        } catch(err) {
            console.error("Error building the dashboard:", err);
        }
    };

    buildDashboard();
    setInterval(buildDashboard, 30*1000);
});
