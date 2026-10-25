
document.addEventListener("DOMContentLoaded", function () {
    const canvas = document.getElementById("riskDistributionChart");

    // This script is only needed on the dashboard page.
    if (!canvas) {
        return;
    }

    const labelsElement = document.getElementById("risk-chart-labels");
    const dataElement = document.getElementById("risk-chart-data");

    if (!labelsElement || !dataElement) {
        console.error("Risk chart data was not found.");
        return;
    }

    const labels = JSON.parse(labelsElement.textContent);
    const values = JSON.parse(dataElement.textContent);

    // Ensure Chart.js has loaded before creating the chart.
    if (typeof Chart === "undefined") {
        console.error("Chart.js did not load.");
        return;
    }

    new Chart(canvas, {
        type: "doughnut",

        data: {
            labels: labels,
            datasets: [{
                label: "Projects",
                data: values,
                backgroundColor: [
                    "#dc2626",
                    "#16a34a",
                    "#94a3b8"
                ],
                borderColor: "#ffffff",
                borderWidth: 3,
                hoverOffset: 8
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    position: "bottom"
                },

                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return `${context.label}: ${context.raw} project(s)`;
                        }
                    }
                }
            }
        }
    });

        // Read the physical progress and expenditure values from Django.
    const progressElement = document.getElementById("physical-progress-data");
    const expenditureElement = document.getElementById("expenditure-data");

    const progressCanvas = document.getElementById("progressExpenditureChart");

    // Run this chart only on pages containing its canvas and data.
    if (progressCanvas && progressElement && expenditureElement) {
        const physicalProgress = JSON.parse(progressElement.textContent);
        const expenditure = JSON.parse(expenditureElement.textContent);

        new Chart(progressCanvas, {
            type: "bar",

            data: {
                labels: ["Physical Progress", "Expenditure"],

                datasets: [{
                    label: "Average Percentage",
                    data: [physicalProgress, expenditure],
                    backgroundColor: ["#2563eb", "#f59e0b"],
                    borderRadius: 6,
                    maxBarThickness: 90
                }]
            },

            options: {
                responsive: true,
                maintainAspectRatio: false,

                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: "Percentage (%)"
                        }
                    }
                },

                plugins: {
                    legend: {
                        display: false
                    },

                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${context.raw.toFixed(1)}%`;
                            }
                        }
                    }
                }
            }
        });
    }


    // Schedule-status distribution chart.
    const statusCanvas = document.getElementById("scheduleStatusChart");
    const statusLabelsElement = document.getElementById("schedule-status-labels");
    const statusDataElement = document.getElementById("schedule-status-data");

    if (statusCanvas && statusLabelsElement && statusDataElement) {
        const statusLabels = JSON.parse(statusLabelsElement.textContent);
        const statusValues = JSON.parse(statusDataElement.textContent);

        new Chart(statusCanvas, {
            type: "doughnut",
            data: {
                labels: statusLabels,
                datasets: [{
                    label: "Projects",
                    data: statusValues,
                    backgroundColor: [
                        "#dc2626",
                        "#64748b",
                        "#16a34a",
                        "#94a3b8"
                    ],
                    borderColor: "#ffffff",
                    borderWidth: 3,
                    hoverOffset: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "bottom"
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                return `${context.label}: ${context.raw} project(s)`;
                            }
                        }
                    }
                }
            }
        });
    }

});
