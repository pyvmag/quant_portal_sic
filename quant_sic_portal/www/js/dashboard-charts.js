google.charts.load('current', { packages: ['corechart'] });
google.charts.setOnLoadCallback(loadData);

function loadData() {
  fetch('charts.json')
    .then(response => response.json())
    .then(data => drawCharts(data));
}

function drawCharts(data) {
  // === 1. Pie Chart (District Distribution) ===
  const districtData = [['District', 'Storage']];
  data.districts.forEach(d => districtData.push([d.name, d.storage]));
  const pieOptions = { title: 'Water Storage by District', pieHole: 0.4 };
  new google.visualization.PieChart(document.getElementById('district_pie'))
    .draw(google.visualization.arrayToDataTable(districtData), pieOptions);

  // === 2. Bar Chart (Taluka % storage) ===
  const talukaPercent = [['Taluka', 'Storage %']];
  data.talukas.forEach(t => talukaPercent.push([t.name, t.percent]));
  const barOptions = {
    title: 'Storage % by Taluka',
    legend: { position: 'none' },
    hAxis: { minValue: 0, maxValue: 100 }
  };
  new google.visualization.BarChart(document.getElementById('taluka_bar'))
    .draw(google.visualization.arrayToDataTable(talukaPercent), barOptions);

  // === 3. Column Chart (Current vs Last Year) ===
  const districtCompare = [['District', 'This Year', 'Last Year']];
  data.districts.forEach(d => districtCompare.push([d.name, d.storage, d.last_year]));
  const columnOptions = {
    title: 'Current vs Last Year Storage (Districts)',
    legend: { position: 'top' }
  };
  new google.visualization.ColumnChart(document.getElementById('district_compare'))
    .draw(google.visualization.arrayToDataTable(districtCompare), columnOptions);

  // === 4. Line Chart (Taluka Capacity vs Storage) ===
  const talukaLine = [['Taluka', 'Capacity', 'Storage']];
  data.talukas.forEach(t => talukaLine.push([t.name, t.capacity, t.storage]));
  const lineOptions = {
    title: 'Taluka Capacity vs Current Storage',
    curveType: 'function',
    legend: { position: 'bottom' }
  };
  new google.visualization.LineChart(document.getElementById('taluka_line'))
    .draw(google.visualization.arrayToDataTable(talukaLine), lineOptions);

  // === 5. Taluka Distribution by % Filled ===
  const gt75 = data.talukas.filter(t => t.percent >= 75).map(t => t.name);
  const btw50_75 = data.talukas.filter(t => t.percent >= 50 && t.percent < 75).map(t => t.name);
  const btw25_50 = data.talukas.filter(t => t.percent >= 25 && t.percent < 50).map(t => t.name);
  const lt25 = data.talukas.filter(t => t.percent < 25).map(t => t.name);

  const distData = [
    ['Category', 'Count', { role: 'annotation' }],
    [`>75% (${gt75.join(', ')})`, gt75.length, gt75.length.toString()],
    [`50–75% (${btw50_75.join(', ')})`, btw50_75.length, btw50_75.length.toString()],
    [`25–50% (${btw25_50.join(', ')})`, btw25_50.length, btw25_50.length.toString()],
    [`<25% (${lt25.join(', ')})`, lt25.length, lt25.length.toString()]
  ];
  const distOptions = {
    title: 'Distribution of Talukas by % Filled',
    legend: { position: 'none' }
  };
  new google.visualization.BarChart(document.getElementById('taluka_dist'))
    .draw(google.visualization.arrayToDataTable(distData), distOptions);
}
