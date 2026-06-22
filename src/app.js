const sectionGrid = document.querySelector("#section-grid");
const directorySection = document.querySelector("[aria-labelledby='sections-title']");
const documentPanel = document.querySelector("#document-panel");
const documentList = document.querySelector("#document-list");
const documentsTitle = document.querySelector("#documents-title");
const activeSectionKicker = document.querySelector("#active-section-kicker");
const generationStamp = document.querySelector("#generation-stamp");
const statusPanel = document.querySelector("#status-panel");
const summaryButtons = document.querySelectorAll("[data-summary-view]");

const archiveManifest = window.archiveManifest;
const sections = archiveManifest.sections;
const mobileViewport = window.matchMedia("(max-width: 640px)");
let activeSummaryView = "station";
let activeSectionId = getInitialSectionId();

const stationStatusItems = [
  {
    label: "Archival Integrity",
    value: "Moderate"
  },
  {
    label: "Clearance",
    value: "Public-ish"
  },
  {
    label: "Interface Language",
    value: "Senate Standard Shasvin"
  }
];

const fileStatusItems = [
  {
    label: "Cleared Files",
    status: "Cleared",
    className: "cleared"
  },
  {
    label: "In Progress Files",
    status: "InProgress",
    className: "in-progress"
  },
  {
    label: "Classified Files",
    status: "Classified",
    className: "classified"
  }
];

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

function getAllDocuments() {
  return sections.flatMap((section) => section.documents);
}

function formatPercentage(count, total) {
  if (total === 0) return "0%";

  return `${Math.round((count / total) * 100)}%`;
}

function renderStatusItem({ label, value, detail, className = "" }) {
  const item = document.createElement("div");
  if (className) item.className = className;

  item.innerHTML = `
    <span class="status-label">${label}</span>
    <strong>${value}</strong>
    ${detail ? `<span class="status-detail">${detail}</span>` : ""}
  `;

  return item;
}

function getFileReportItems() {
  const documents = getAllDocuments();
  const total = documents.length;

  return fileStatusItems.map((item) => {
    const count = documents.filter((document) => document.status === item.status).length;

    return {
      label: item.label,
      value: formatPercentage(count, total),
      detail: `${count} of ${total} file${total === 1 ? "" : "s"}`,
      className: item.className
    };
  });
}

function renderSummary() {
  summaryButtons.forEach((button) => {
    const isActive = button.dataset.summaryView === activeSummaryView;
    button.setAttribute("aria-pressed", isActive ? "true" : "false");
  });

  const items = activeSummaryView === "files" ? getFileReportItems() : stationStatusItems;
  statusPanel.replaceChildren(...items.map(renderStatusItem));
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
        render({ scrollToDirectory: mobileViewport.matches });
      });

      return button;
    })
  );
}

function scrollDirectoryIntoView() {
  if (!directorySection) return;

  window.requestAnimationFrame(() => {
    const directoryTop = directorySection.getBoundingClientRect().top;
    const scrollMargin = 10;
    const targetTop = window.scrollY + directoryTop - scrollMargin;

    if (targetTop <= window.scrollY) return;

    window.scrollTo({
      top: targetTop,
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"
    });
  });
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

function render({ scrollToDirectory = false } = {}) {
  renderSummary();
  renderSections();
  renderDocuments();

  if (scrollToDirectory) {
    scrollDirectoryIntoView();
  }
}

generationStamp.textContent = formatTimestamp(archiveManifest.generatedAt);
summaryButtons.forEach((button) => {
  button.addEventListener("click", () => {
    activeSummaryView = button.dataset.summaryView;
    renderSummary();
  });
});
render();
