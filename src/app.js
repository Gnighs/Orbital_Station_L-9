const sectionGrid = document.querySelector("#section-grid");
const documentPanel = document.querySelector("#document-panel");
const documentList = document.querySelector("#document-list");
const documentsTitle = document.querySelector("#documents-title");
const activeSectionKicker = document.querySelector("#active-section-kicker");
const generationStamp = document.querySelector("#generation-stamp");

const archiveManifest = window.archiveManifest;
const sections = archiveManifest.sections;
let activeSectionId = getInitialSectionId();

function getInitialSectionId() {
  const hash = window.location.hash.replace(/^#/, "");
  if (sections.some((section) => section.id === hash)) return hash;

  return null;
}

function formatTimestamp(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";

  return `Index refreshed ${date.toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric"
  })}`;
}

function renderSections() {
  sectionGrid.replaceChildren(
    ...sections.map((section) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `section-card ${section.status}`;
      button.dataset.active = section.id === activeSectionId ? "true" : "false";
      button.setAttribute("aria-pressed", section.id === activeSectionId ? "true" : "false");

      const status = section.status === "available" ? `${section.count} file${section.count === 1 ? "" : "s"} indexed` : section.maintenanceLine;

      button.innerHTML = `
        <span class="card-topline">
          <span>${section.id.toUpperCase()}</span>
          <span>${section.status === "available" ? "FOLDER" : "MAINT"}</span>
        </span>
        <strong>${section.title}</strong>
        <span class="card-copy">${section.description}</span>
        <span class="card-status">${status}</span>
      `;

      button.addEventListener("click", () => {
        activeSectionId = section.id;
        window.history.replaceState(null, "", `#${section.id}`);
        render();
      });

      return button;
    })
  );
}

function documentRow(file, section) {
  const row = document.createElement(file.isAvailable ? "a" : "article");
  row.className = `document-row ${file.className ?? "cleared"} ${file.isAvailable ? "available" : "unavailable"}`;

  if (file.isAvailable) {
    row.href = file.href;
    row.target = "_blank";
    row.rel = "noopener";
  } else {
    row.setAttribute("aria-disabled", "true");
  }

  row.innerHTML = `
    <span class="document-id">${file.id}</span>
    <span class="document-main">
      <strong>${file.title}</strong>
      <span>${file.statusLabel ?? "Current Archive Copy"}</span>
    </span>
    <span class="document-action">${file.actionLabel ?? "View PDF"}</span>
  `;

  return row;
}

function maintenanceNotice(section) {
  const article = document.createElement("article");
  article.className = "maintenance-notice";
  article.innerHTML = `
    <span>${section.maintenanceLine}</span>
    <strong>${section.emptyTitle}</strong>
    <p>${section.emptyMessage}</p>
  `;
  return article;
}

function renderDocuments() {
  const activeSection = sections.find((section) => section.id === activeSectionId);

  if (!activeSection) {
    documentPanel.hidden = true;
    documentList.replaceChildren();
    return;
  }

  documentPanel.hidden = false;
  documentsTitle.textContent = activeSection.title;
  activeSectionKicker.textContent = activeSection.status === "available" ? "Open Index" : "Restricted Index";

  if (activeSection.documents.length === 0) {
    documentList.replaceChildren(maintenanceNotice(activeSection));
    return;
  }

  documentList.replaceChildren(
    ...activeSection.documents.map((document) => documentRow(document, activeSection))
  );
}

function render() {
  renderSections();
  renderDocuments();
}

generationStamp.textContent = formatTimestamp(archiveManifest.generatedAt);
render();
