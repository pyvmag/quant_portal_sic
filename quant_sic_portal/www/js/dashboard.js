document.addEventListener('DOMContentLoaded', () => {
    const dataPath = '/sites/assets/sicsangli/data/data1.json';

    const fetchData = async (path) => {
        const response = await fetch(path);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    };

    fetchData(dataPath)
        .then(data => {
            const cleanData = data.slice(2).filter(row => {
                const srNo = row ? row['अ.क्र.'] : null;
                return srNo !== null && String(srNo).trim() !== '' && !isNaN(parseInt(srNo));
            });

            if (cleanData.length === 0) {
                console.error("No valid data rows found after cleaning.");
                return;
            }

            // --- Calculate and Display KPIs ---
            displayKPIs(cleanData);

            // --- Create All Charts ---
            createStorageByDistrictChart(cleanData);
            createStorageByTypeChart(cleanData);
            createTopDamsChart(cleanData);
            createDamsByTalukaChart(cleanData);
        })
        .catch(error => {
            console.error("Error building the dashboard:", error);
        });
});

function displayKPIs(data) {
    // Total Dams
    document.getElementById('total-dams').innerText = data.length;

    // Average Storage Percentage
    const totalPercentage = data.reduce((sum, row) => sum + (parseFloat(row.__3) || 0), 0);
    const avgPercentage = totalPercentage / data.length;
    document.getElementById('avg-storage').innerText = `${avgPercentage.toFixed(1)}%`;

    // Dams above 90%
    const damsAbove90 = data.filter(row => (parseFloat(row.__3) || 0) >= 90).length;
    document.getElementById('dams-above-90').innerText = damsAbove90;
}

function createStorageByDistrictChart(data) {
    const ctx = document.getElementById('storageByDistrictChart').getContext('2d');
    const districtData = data.reduce((acc, row) => {
        const district = row.जिल्हा ? row.जिल्हा.trim() : 'Unknown';
        if (!acc[district]) acc[district] = 0;
        acc[district] += parseFloat(row.__2) || 0; // __2 is 'एकूण पाणीसाठा' (Total Storage)
        return acc;
    }, {});

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(districtData),
            datasets: [{
                label: 'Total Storage (MCFT)',
                data: Object.values(districtData),
                backgroundColor: ['#007bff', '#28a745', '#ffc107', '#dc3545', '#17a2b8'],
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { title: { display: true, text: 'Total Water Storage by District' } }
        }
    });
}

function createStorageByTypeChart(data) {
    const ctx = document.getElementById('storageByTypeChart').getContext('2d');
    const typeData = data.reduce((acc, row) => {
        const type = row['प्रकल्प प्रकार'] ? row['प्रकल्प प्रकार'].trim() : 'Unknown';
        if (!acc[type]) acc[type] = 0;
        acc[type] += parseFloat(row.__2) || 0; // __2 is 'एकूण पाणीसाठा' (Total Storage)
        return acc;
    }, {});

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(typeData),
            datasets: [{
                label: 'Total Storage (MCFT)',
                data: Object.values(typeData),
                backgroundColor: '#28a745',
            }]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { title: { display: true, text: 'Total Storage by Project Type' } },
            scales: { y: { beginAtZero: true } }
        }
    });
}

function createTopDamsChart(data) {
    const ctx = document.getElementById('topDamsChart').getContext('2d');
    const top10Data = data
        .sort((a, b) => (parseFloat(b.__2) || 0) - (parseFloat(a.__2) || 0)) // Sort by Total Storage
        .slice(0, 10);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: top10Data.map(d => d['धरणाचे नाव']),
            datasets: [{
                label: 'Total Storage (MCFT)',
                data: top10Data.map(d => parseFloat(d.__2) || 0),
                backgroundColor: '#ffc107',
            }]
        },
        options: {
            indexAxis: 'y', // Horizontal Bar Chart
            responsive: true, maintainAspectRatio: false,
            plugins: { title: { display: true, text: 'Top 10 Dams by Total Storage Capacity' } },
            scales: { x: { beginAtZero: true } }
        }
    });
}

function createDamsByTalukaChart(data) {
    const ctx = document.getElementById('damsByTalukaChart').getContext('2d');
    const talukaData = data.reduce((acc, row) => {
        const taluka = row.तालुका ? row.तालुका.trim() : 'Unknown';
        if (!acc[taluka]) acc[taluka] = 0;
        acc[taluka]++;
        return acc;
    }, {});

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: Object.keys(talukaData),
            datasets: [{
                label: 'Number of Dams',
                data: Object.values(talukaData),
                backgroundColor: '#dc3545',
            }]
        },
        options: {
            indexAxis: 'y', // Horizontal Bar Chart for readability
            responsive: true, maintainAspectRatio: false,
            plugins: { title: { display: true, text: 'Number of Dams per Taluka' } },
            scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } }
        }
    });
}