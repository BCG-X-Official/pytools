$(document).ready(function() {
    $('a.reference.external').attr('target', '_blank');
    DOCUMENTATION_OPTIONS.VERSION = DOCS_VERSIONS.current;
    buildVersionSelector();
});


const buildVersionSelector = function() {

    const versionSelector = $('<select/>');

    versionSelector.change(function() {
        navigateToDocsVersion($(this).val());
    });

    const activeDocsVersion = getActiveDocsVersion()

    DOCS_VERSIONS.non_rc.forEach(function(docsVersion) {
        versionSelector
            .append($('<option/>')
                .html("Version: " + docsVersion)
                .attr("value", docsVersion)
                .attr("selected", docsVersion === activeDocsVersion)
            );
    });

    $("#navbar-menu").append(versionSelector);
}

const getActiveDocsVersion = function() {
    const currentLocation = window.location + "";
    if (currentLocation.indexOf("index.html") > 0) {
        return DOCS_VERSIONS.current;
    } else {
        const rExp = /.*docs-version\/(\d-\d-\d.*)\/.*/g;
        const matches = rExp.exec(currentLocation);
        if (matches.length > 1) {
            // convert back from URL to real version string
            return matches[1].split("-").join(".");
        }
    }
    return DOCS_VERSIONS.current;
}

const navigateToDocsVersion = function(targetVersion) {
    const currentLocation = window.location + "";
    let newLocation = currentLocation;

    if (targetVersion === DOCS_VERSIONS.current) {
        newLocation = "index.html";
    } else {
        const subUrl = "docs-version/" + targetVersion.split(".").join("-") + "/";
        if (currentLocation.indexOf("docs-version/") > 0) {
            const startIndex = currentLocation.indexOf("docs-version/")
            newLocation = currentLocation.substring(0, startIndex) + subUrl
        } else {
            newLocation = subUrl
        }
    }

    window.location = newLocation;
}