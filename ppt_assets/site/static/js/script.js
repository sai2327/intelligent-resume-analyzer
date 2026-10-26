document.addEventListener("DOMContentLoaded", () => {
  const ALLOWED_EXTENSIONS = ["pdf", "docx"];
  const MAX_SIZE_MB = 10;

  function updateDropZoneLabel(zone, file) {
    const hint = zone.querySelector(".drop-zone__hint");
    if (hint) hint.textContent = `Selected: ${file.name}`;
  }

  document.querySelectorAll(".drop-zone").forEach((zone) => {
    const input = zone.querySelector("input[type='file']");
    if (!input) return;

    zone.addEventListener("dragover", (event) => {
      event.preventDefault();
      zone.classList.add("drop-zone--over");
    });
    zone.addEventListener("dragleave", () => zone.classList.remove("drop-zone--over"));
    zone.addEventListener("drop", (event) => {
      event.preventDefault();
      zone.classList.remove("drop-zone--over");
      if (event.dataTransfer.files.length) {
        input.files = event.dataTransfer.files;
        updateDropZoneLabel(zone, input.files[0]);
      }
    });
    input.addEventListener("change", () => {
      if (input.files.length) updateDropZoneLabel(zone, input.files[0]);
    });
  });

  function validateFile(file) {
    if (!file) return null;
    const ext = file.name.split(".").pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Unsupported file type '.${ext}'. Please upload a PDF or DOCX file.`;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File is too large. Maximum allowed size is ${MAX_SIZE_MB} MB.`;
    }
    return null;
  }

  document.querySelectorAll("form.upload-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const errorBox = document.getElementById("clientError");
      const inputsToCheck = ["resume_file", "jd_file"];

      for (const name of inputsToCheck) {
        const input = form.querySelector(`input[name='${name}']`);
        if (input && input.files.length) {
          const error = validateFile(input.files[0]);
          if (error) {
            event.preventDefault();
            if (errorBox) {
              errorBox.textContent = error;
              errorBox.classList.remove("d-none");
            }
            return;
          }
        }
      }

      if (errorBox) errorBox.classList.add("d-none");
      const loading = document.getElementById("loadingIndicator");
      if (loading) loading.classList.remove("d-none");
    });
  });
});
