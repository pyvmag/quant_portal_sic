const sheetId = '1uZMDUujtlQr_G5E720P0upyQJ2Pfwiu_m8DIorZZyvA';  // Replace with your Google Sheet ID
const apiKey = 'AIzaSyB5tMhLVyDWwN5ECJzbFTn2eEpsuTkCLPg';          // Replace with your Google API Key



// Construct the Google Sheets API URL
const sheetUrl = `https://sheets.googleapis.com/v4/spreadsheets/${sheetId}/values:batchGet?key=${apiKey}&ranges=Sheet1`;

// Fetch the data from Google Sheets API
async function fetchSheetData() {
  try {
    const response = await fetch(sheetUrl);
    const data = await response.json();
    
    // Log the raw API response to see what we're getting
    console.log("API Response Data: ", data);

    // Check if we received data
    if (data.error) {
      console.error('Error fetching data:', data.error.message);
      return;
    }

    // Parse the sheet data (check if it's available)
    if (data.valueRanges && data.valueRanges[0].values) {
      const parsedData = parseData(data.valueRanges[0].values);
      console.log("Parsed Data: ", parsedData); // Log parsed data to verify

      // Create charts with the parsed data
      createCharts(parsedData);
    } else {
      console.error('No valid data found in the response.');
    }
  } catch (error) {
    console.error('Error fetching data from Google Sheets:', error);
  }
}

// Parse the data from Google Sheets response
function parseData(data) {
  const labels = data.map(row => row[0] || '');  // First column as labels
  const values = data.map(row => parseInt(row[1], 10) || 0); // Second column as numeric values

  return { labels, values };
}

// Create charts using the parsed data
function createCharts(parsedData) {
  const { labels, values } = parsedData;

  if (labels.length === 0 || values.length === 0) {
    console.error('Invalid data: No valid labels or values.');
    return;
  }

  // Create Pie Chart
  const pieCtx = document.getElementById('myPieChart').getContext('2d');
  new Chart(pieCtx, {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#c2c2f0', '#ffb3e6', '#ff6666', '#c2f0c2'],
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'top' },
        tooltip: { enabled: true }
      }
    }
  });

  // Create Bar Chart
  const barCtx = document.getElementById('myBarChart').getContext('2d');
  new Chart(barCtx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Data Label',
        data: values,
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        borderColor: 'rgba(54, 162, 235, 1)',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      scales: { x: { beginAtZero: true } },
      plugins: { legend: { position: 'top' } }
    }
  });

  // Create Line Chart
  const lineCtx = document.getElementById('myLineChart').getContext('2d');
  new Chart(lineCtx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Data Label',
        data: values,
        borderColor: 'rgba(75, 192, 192, 1)',
        fill: false
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { position: 'top' } }
    }
  });
}

// Call the function to fetch data from Google Sheets after page loads
window.onload = function() {
  fetchSheetData();
};

