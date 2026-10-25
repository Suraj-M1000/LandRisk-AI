
document.addEventListener("DOMContentLoaded", function () {
    const predictionForm = document.getElementById("prediction-form");
    const predictButton = document.getElementById("predict-button");
    const predictionStatus = document.getElementById("prediction-status");

    // Stop if this page does not contain the prediction form.
    if (!predictionForm || !predictButton || !predictionStatus) {
        return;
    }

    predictionForm.addEventListener("submit", function () {
        // Avoid processing another submission through this form.
        if (predictButton.disabled) {
            return;
        }

        predictButton.disabled = true;
        predictButton.textContent = "Generating prediction…";

        predictionStatus.textContent =
            "Please wait while the risk assessment is generated.";
    });
});
