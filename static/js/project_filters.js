
document.addEventListener("DOMContentLoaded", function () {
    // Get the search and filter controls.
    const searchInput = document.getElementById("project-search");
    const sectorFilter = document.getElementById("sector-filter");
    const stateFilter = document.getElementById("state-filter");
    const resetButton = document.getElementById("reset-filters");
    const emptyResetButton = document.getElementById("empty-reset-filters");

    // Get all project cards and the result messages.
    const projectItems = document.querySelectorAll(".project-item");
    const resultsCount = document.getElementById("results-count");
    const noMatchingMessage = document.getElementById("no-matching-projects");

    // Apply the current search and filter values.
    function filterProjects() {
        const searchText = searchInput.value.trim().toLowerCase();
        const selectedSector = sectorFilter.value.toLowerCase();
        const selectedState = stateFilter.value.toLowerCase();

        let visibleCount = 0;

        projectItems.forEach(function (project) {
            const name = project.dataset.name;
            const sector = project.dataset.sector;
            const state = project.dataset.state;

            const matchesName = name.includes(searchText);

            const matchesSector =
                selectedSector === "" || sector === selectedSector;

            const matchesState =
                selectedState === "" || state === selectedState;

            const isMatch =
                matchesName && matchesSector && matchesState;

            project.hidden = !isMatch;

            if (isMatch) {
                visibleCount++;
            }
        });

        // Update the visible project count.
        resultsCount.textContent =
            `Showing ${visibleCount} of ${projectItems.length} project(s)`;

        // Show the empty state only when projects exist but none match.
        noMatchingMessage.hidden =
            projectItems.length === 0 || visibleCount !== 0;
    }

    // Reset every filter and refresh the project list.
    function resetFilters() {
        searchInput.value = "";
        sectorFilter.value = "";
        stateFilter.value = "";

        filterProjects();
        searchInput.focus();
    }

    // Listen for search and filter changes.
    searchInput.addEventListener("input", filterProjects);
    sectorFilter.addEventListener("change", filterProjects);
    stateFilter.addEventListener("change", filterProjects);

    // Both reset buttons perform the same action.
    resetButton.addEventListener("click", resetFilters);

    if (emptyResetButton) {
        emptyResetButton.addEventListener("click", resetFilters);
    }

    // Initialize the project count.
    filterProjects();
});
