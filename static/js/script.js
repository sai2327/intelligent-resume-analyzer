document.addEventListener("DOMContentLoaded", () => {
  const ALLOWED_EXTENSIONS = ["pdf", "docx"];
  const MAX_SIZE_MB = 10;

  function formatBytes(bytes, decimals = 1) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
  }

  function updateDropZoneLabel(zone, files) {
    const hint = zone.querySelector(".drop-zone__hint");
    const title = zone.querySelector(".drop-zone__title");
    if (!files || files.length === 0) return;

    if (files.length === 1) {
      const file = files[0];
      const sizeStr = formatBytes(file.size);
      if (hint) {
        hint.innerHTML = `<span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1"><i class="bi bi-check-circle me-1"></i>Selected: <strong>${file.name}</strong> (${sizeStr})</span>`;
      }
      if (title) {
        title.textContent = "File selected. Click or drag to change.";
      }
    } else {
      const totalSize = Array.from(files).reduce((acc, f) => acc + f.size, 0);
      const names = Array.from(files).map(f => f.name).slice(0, 3).join(", ");
      const more = files.length > 3 ? ` (+${files.length - 3} more)` : "";
      if (hint) {
        hint.innerHTML = `<span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1"><i class="bi bi-check-circle me-1"></i>Selected ${files.length} files: <strong>${names}${more}</strong> (${formatBytes(totalSize)})</span>`;
      }
      if (title) {
        title.textContent = `${files.length} files selected. Click or drag to change.`;
      }
    }
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
      if (event.dataTransfer && event.dataTransfer.files.length) {
        input.files = event.dataTransfer.files;
        updateDropZoneLabel(zone, input.files);
      }
    });

    input.addEventListener("change", () => {
      if (input.files.length) {
        updateDropZoneLabel(zone, input.files);
      }
    });
  });

  function validateFile(file) {
    if (!file) return null;
    const ext = file.name.split(".").pop().toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Unsupported file type '.${ext}'. Please upload a PDF or DOCX file.`;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File '${file.name}' is too large. Maximum allowed size is ${MAX_SIZE_MB} MB.`;
    }
    return null;
  }

  document.querySelectorAll("form.upload-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const errorBox = document.getElementById("clientError");
      const inputsToCheck = ["resume_file", "jd_file", "resume_files"];

      for (const name of inputsToCheck) {
        const input = form.querySelector(`input[name='${name}']`);
        if (input && input.files && input.files.length) {
          for (const file of Array.from(input.files)) {
            const error = validateFile(file);
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
      }

      if (errorBox) errorBox.classList.add("d-none");
      const loading = document.getElementById("loadingIndicator");
      if (loading) loading.classList.remove("d-none");
    });
  });
});
