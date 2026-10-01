/**
 * annotate.js — Core Interaction Loop & Keyboard Shortcuts
 * Bangla Meme Propaganda HITL Verification System
 */

document.addEventListener("DOMContentLoaded", () => {
  const drawer = document.getElementById("correctionDrawer");
  const formAction = document.getElementById("formAction");
  const drawerTitle = document.getElementById("drawerModeTitle");
  const techniqueSelect = document.getElementById("technique_label");
  const evidenceInput = document.getElementById("evidence_span");
  const btnAccept = document.getElementById("btnAccept");
  const btnEdit = document.getElementById("btnEdit");
  const btnReject = document.getElementById("btnReject");
  const btnSkip = document.getElementById("btnSkip");
  const btnCancel = document.getElementById("btnCancelCorrection");
  const btnClose = document.getElementById("btnCloseDrawer");
  const linkPrev = document.getElementById("linkPrev");
  const linkNext = document.getElementById("linkNext");
  const ocrContainer = document.getElementById("ocrTextContainer");

  // Open drawer in EDIT mode
  function openEditDrawer() {
    if (!drawer) return;
    drawer.classList.add("open");
    if (formAction) formAction.value = "edit";
    if (drawerTitle) drawerTitle.textContent = "EDIT PREDICTION / CORRECT ANNOTATION";
    if (techniqueSelect) techniqueSelect.focus();
  }

  // Open drawer in REJECT mode
  function openRejectDrawer() {
    if (!drawer) return;
    drawer.classList.add("open");
    if (formAction) formAction.value = "reject";
    if (drawerTitle) drawerTitle.textContent = "REJECT PREDICTION / CHOOSE ALTERNATIVE (DEFAULT: T08)";
    if (techniqueSelect) {
      techniqueSelect.value = "T08"; // Default to No Propaganda on rejection
      techniqueSelect.focus();
    }
  }

  // Close drawer
  function closeDrawer() {
    if (!drawer) return;
    drawer.classList.remove("open");
  }

  // Bind click handlers
  if (btnEdit) {
    btnEdit.addEventListener("click", (e) => {
      e.preventDefault();
      if (drawer.classList.contains("open") && formAction.value === "edit") {
        closeDrawer();
      } else {
        openEditDrawer();
      }
    });
  }

  if (btnReject) {
    btnReject.addEventListener("click", (e) => {
      e.preventDefault();
      if (drawer.classList.contains("open") && formAction.value === "reject") {
        closeDrawer();
      } else {
        openRejectDrawer();
      }
    });
  }

  if (btnCancel) {
    btnCancel.addEventListener("click", (e) => {
      e.preventDefault();
      closeDrawer();
    });
  }

  if (btnClose) {
    btnClose.addEventListener("click", (e) => {
      e.preventDefault();
      closeDrawer();
    });
  }

  // Helper: auto-capture selected text from OCR block into evidence input
  if (ocrContainer && evidenceInput) {
    ocrContainer.addEventListener("mouseup", () => {
      const selected = window.getSelection().toString().trim();
      if (selected.length > 0) {
        evidenceInput.value = selected;
        // If drawer is closed, open it in edit mode
        if (drawer && !drawer.classList.contains("open")) {
          openEditDrawer();
        }
      }
    });
  }

  // Keyboard Shortcuts Handler
  document.addEventListener("keydown", (e) => {
    const activeEl = document.activeElement;
    const isTyping =
      activeEl &&
      (activeEl.tagName === "INPUT" ||
       activeEl.tagName === "TEXTAREA" ||
       activeEl.tagName === "SELECT");

    // Escape closes the drawer regardless of focus
    if (e.key === "Escape") {
      if (drawer && drawer.classList.contains("open")) {
        closeDrawer();
        e.preventDefault();
        return;
      }
    }

    // When drawer is open and user presses Enter inside an input
    if (isTyping) {
      return; // Do not trigger letter shortcuts while typing in inputs
    }

    const key = e.key.toLowerCase();

    if (key === "a") {
      // ACCEPT
      if (btnAccept) {
        e.preventDefault();
        btnAccept.click();
      }
    } else if (key === "e") {
      // EDIT
      e.preventDefault();
      openEditDrawer();
    } else if (key === "r") {
      // REJECT
      e.preventDefault();
      openRejectDrawer();
    } else if (key === "s") {
      // SKIP
      if (btnSkip) {
        e.preventDefault();
        btnSkip.click();
      }
    } else if (e.key === "ArrowLeft") {
      // PREVIOUS POST
      if (linkPrev) {
        e.preventDefault();
        linkPrev.click();
      }
    } else if (e.key === "ArrowRight") {
      // NEXT POST
      if (linkNext) {
        e.preventDefault();
        linkNext.click();
      }
    }
  });
});
