/**
 * klasterisasi.js - Script untuk mengelola halaman klasterisasi
 *
 * Mengintegrasikan klasterisasi.html dengan backend (app.py dan ClusteringManager.py)
 * untuk menampilkan dan mengelola data klasterisasi wilayah berdasarkan indikator
 * kualitas pendidikan.
 */

// Namespace untuk klasterisasi untuk menghindari pollusi global
const Klasterisasi = {
  // State management
  state: {
    currentTab: "import-data-tab",
    sidebarCollapsed: false,
    loadingStates: {
      results: false,
      characteristics: false,
      evaluation: false,
    },
    data: {
      results: [],
      characteristics: [],
      evaluation: {},
      selectedResult: null,
      selectedCluster: null,
    },
    ui: {
      characteristicsView: "card", // 'card' or 'table'
      evaluationView: "summary", // 'summary' or 'detail'
    },
  },

  // Konstanta untuk endpoint API
  API: {
    RESULTS: "/klasterisasi/api/results",
    CLUSTERS: "/klasterisasi/api/clusters/",
    CHARACTERISTICS: "/klasterisasi/api/characteristics/",
    DETAILED_CHARACTERISTICS: "/klasterisasi/api/detailed_characteristics/",
    EVALUATION: "/klasterisasi/api/evaluasi/",
    KECAMATAN: "/klasterisasi/api/kecamatan/",
    KECAMATAN_DATA: "/klasterisasi/api/kecamatan_data/",
    KECAMATAN_DETAIL: "/klasterisasi/api/kecamatan_detail/",
    SEKOLAH: "/klasterisasi/api/sekolah/",
    SEKOLAH_DETAIL: "/klasterisasi/api/sekolah_detail/",
    PREVIEW_CSV: "/klasterisasi/preview_csv",
    DELETE_RESULT: "/klasterisasi/delete/",
    CHECK_QUALITY: "/klasterisasi/check_quality/",
    FIX_ISSUES: "/klasterisasi/fix_issues/",
    OPTIMIZE: "/klasterisasi/optimize/",
  },

  /**
   * Inisialisasi aplikasi klasterisasi
   */
  init: function () {
    // Setelah DOM ready, setup event listeners
    document.addEventListener("DOMContentLoaded", () => {
      this.setupEventListeners();
      this.initTabs();
      this.loadInitialData();
      this.initModal();
      this.updateDashboardStats();
    });
  },

  /**
   * Setup event listeners untuk interaksi UI
   */
  setupEventListeners: function () {
    // Tab navigation
    document.querySelectorAll(".tab-btn").forEach((tab) => {
      tab.addEventListener("click", (e) => {
        const targetId = tab.getAttribute("data-target");
        this.switchTab(targetId, tab);
      });
    });

    // Sidebar toggle
    const sidebarToggleBtn = document.getElementById("collapse-sidebar");
    if (sidebarToggleBtn) {
      sidebarToggleBtn.addEventListener("click", this.toggleSidebar.bind(this));
    }

    // Flash message close buttons
    document.querySelectorAll(".alert-close").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const alert = e.currentTarget.closest(".alert");
        if (alert) {
          alert.remove();
        }
      });
    });

    // Import data tab
    this.importModule.setupEventListeners();

    // Hasil klasterisasi tab
    this.hasilModule.setupEventListeners();

    // Analisis karakteristik tab
    this.karakteristikModule.setupEventListeners();

    // Evaluasi standar tab
    this.evaluasiModule.setupEventListeners();

    // Empty state actions
    const emptyStateImportBtn = document.getElementById(
      "empty-state-import-btn"
    );
    if (emptyStateImportBtn) {
      emptyStateImportBtn.addEventListener("click", () => {
        this.switchTab(
          "import-data-content",
          document.getElementById("import-data-tab")
        );
      });
    }
  },

  /**
   * Inisialisasi tab dan menampilkan tab aktif
   */
  initTabs: function () {
    // Tampilkan tab default (import-data)
    this.switchTab(
      "import-data-content",
      document.getElementById("import-data-tab")
    );
  },

  /**
   * Switch tab yang aktif
   * @param {string} tabId - ID dari tab content yang akan ditampilkan
   * @param {HTMLElement} tabButton - Button tab yang diklik
   */
  switchTab: function (tabId, tabButton) {
    // Sembunyikan semua tab content
    document.querySelectorAll(".tab-pane").forEach((tab) => {
      tab.classList.add("hidden");
    });

    // Hapus kelas active dari semua tab buttons
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.classList.remove("active-tab");
      btn.querySelector("svg").classList.remove("text-purple-600");
      btn.querySelector("svg").classList.add("text-gray-600");
    });

    // Tampilkan tab yang dipilih
    const tabContent = document.getElementById(tabId);
    if (tabContent) {
      tabContent.classList.remove("hidden");
    }

    // Tandai tab button aktif
    if (tabButton) {
      tabButton.classList.add("active-tab");
      tabButton.querySelector("svg").classList.remove("text-gray-600");
      tabButton.querySelector("svg").classList.add("text-purple-600");
      this.state.currentTab = tabButton.id;

      // Load data khusus untuk tab tertentu jika diperlukan
      switch (tabId) {
        case "hasil-content":
          this.hasilModule.loadResults();
          break;
        case "karakteristik-content":
          this.karakteristikModule.initFilterOptions();
          break;
        case "evaluasi-content":
          this.evaluasiModule.initFilterOptions();
          break;
      }
    }
  },

  /**
   * Toggle sidebar collapse/expand
   */
  toggleSidebar: function () {
    const sidebar = document.getElementById("sidebar");
    const mainContent = document.getElementById("main-content");
    const collapseIcon = document.getElementById("collapse-icon");
    const expandIcon = document.getElementById("expand-icon");
    const sidebarTexts = document.querySelectorAll(".sidebar-text");

    if (!this.state.sidebarCollapsed) {
      // Collapse sidebar
      sidebar.style.width = "60px";
      mainContent.style.marginLeft = "60px";
      collapseIcon.classList.add("hidden");
      expandIcon.classList.remove("hidden");
      sidebarTexts.forEach((el) => {
        el.classList.add("hidden");
      });
    } else {
      // Expand sidebar
      sidebar.style.width = "256px";
      mainContent.style.marginLeft = "256px";
      collapseIcon.classList.remove("hidden");
      expandIcon.classList.add("hidden");
      sidebarTexts.forEach((el) => {
        el.classList.remove("hidden");
      });
    }

    this.state.sidebarCollapsed = !this.state.sidebarCollapsed;
  },

  /**
   * Load data awal untuk dashboard
   */
  loadInitialData: function () {
    this.fetchResults()
      .then((results) => {
        this.state.data.results = results;
        this.updateDashboardStats();
      })
      .catch((error) => {
        console.error("Error loading initial data:", error);
        this.utils.showErrorMessage(
          "Gagal memuat data. Silahkan refresh halaman."
        );
      });
  },

  /**
   * Fetch data hasil klasterisasi dari API
   * @returns {Promise} - Promise yang menghasilkan data hasil klasterisasi
   */
  fetchResults: function () {
    return fetch(this.API.RESULTS)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((data) => {
        if (data.results) {
          return data.results;
        }
        return [];
      });
  },

  /**
   * Update statistik dashboard berdasarkan data yang dimuat
   */
  updateDashboardStats: function () {
    const results = this.state.data.results;

    // Update total count
    const totalCount = document.getElementById("total-hasil-count");
    if (totalCount) {
      totalCount.textContent = results.length;
    }

    // Hitung jumlah hasil untuk SMA dan SMK
    const smaResults = results.filter((r) => r.jenjang === "SMA");
    const smkResults = results.filter((r) => r.jenjang === "SMK");

    // Update SMA stats
    const smaCount = document.getElementById("total-sma-count");
    const smaKlasterCount = document.getElementById("sma-klaster-count");
    if (smaCount) {
      smaCount.textContent = smaResults.length;
    }
    if (smaKlasterCount) {
      const totalSmaKlaster = smaResults.reduce(
        (sum, item) => sum + (item.jumlah_cluster || 0),
        0
      );
      smaKlasterCount.textContent = `${totalSmaKlaster} klaster`;
    }

    // Update SMK stats
    const smkCount = document.getElementById("total-smk-count");
    const smkKlasterCount = document.getElementById("smk-klaster-count");
    if (smkCount) {
      smkCount.textContent = smkResults.length;
    }
    if (smkKlasterCount) {
      const totalSmkKlaster = smkResults.reduce(
        (sum, item) => sum + (item.jumlah_cluster || 0),
        0
      );
      smkKlasterCount.textContent = `${totalSmkKlaster} klaster`;
    }

    // Update total kecamatan
    const totalKecamatan = document.getElementById("total-kecamatan");
    if (totalKecamatan) {
      const kecamatanCount = results.reduce(
        (sum, item) => sum + (item.kecamatan_count || 0),
        0
      );
      totalKecamatan.textContent = `${kecamatanCount} kecamatan`;
    }
  },

  /**
   * Inisialisasi modal dialog
   */
  initModal: function () {
    // Tambahkan event listener untuk semua tombol close modal
    document.querySelectorAll(".close-modal").forEach((button) => {
      button.addEventListener("click", (e) => {
        const modal = e.target.closest('[id$="-modal"]');
        if (modal) {
          this.closeModal(modal.id);
        }
      });
    });

    // Tutup modal ketika klik di overlay
    document.querySelectorAll('[id$="-modal"]').forEach((modal) => {
      modal.addEventListener("click", (e) => {
        if (e.target === modal) {
          this.closeModal(modal.id);
        }
      });
    });
  },

  /**
   * Buka modal dengan ID tertentu
   * @param {string} modalId - ID modal yang akan dibuka
   */
  openModal: function (modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove("hidden");
      modal.classList.add("flex");
      document.body.classList.add("overflow-hidden");
    }
  },

  /**
   * Tutup modal dengan ID tertentu
   * @param {string} modalId - ID modal yang akan ditutup
   */
  closeModal: function (modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
      modal.classList.remove("flex");
      modal.classList.add("hidden");
      document.body.classList.remove("overflow-hidden");
    }
  },

  /**
   * Module untuk tab Import Data
   */
  importModule: {
    /**
     * Setup event listeners untuk tab Import Data
     */
    setupEventListeners: function () {
      // File upload untuk hasil klasterisasi
      const clusterFileUpload = document.getElementById("cluster-file-upload");
      if (clusterFileUpload) {
        clusterFileUpload.addEventListener(
          "change",
          this.handleClusterFileUpload.bind(this)
        );
      }

      // File upload untuk data sekolah
      const sekolahFileUpload = document.getElementById("sekolah-file-upload");
      if (sekolahFileUpload) {
        sekolahFileUpload.addEventListener(
          "change",
          this.handleSekolahFileUpload.bind(this)
        );
      }

      // Form submission untuk import hasil klasterisasi
      const importForm = document.querySelector('form[action*="create_process"]');
      if (importForm) {
        importForm.addEventListener(
          "submit",
          this.handleImportSubmit.bind(this)
        );
      }

      // Form submission untuk import data sekolah
      const importSekolahForm = document.querySelector('form[action*="import_sekolah_data"]');
      if (importSekolahForm) {
        importSekolahForm.addEventListener(
          "submit",
          this.handleImportSekolahSubmit.bind(this)
        );
      }

      // Setup event handlers untuk ekspor dan backup data
      this.setupExportHandlers();
      this.setupBackupHandlers();

      // File upload untuk restore
      const backupFileInput = document.getElementById("backup-file");
      if (backupFileInput) {
        backupFileInput.addEventListener("change", function () {
          const filenameEl = document.getElementById("backup-filename");
          if (filenameEl && this.files && this.files.length > 0) {
            filenameEl.textContent = this.files[0].name;
          }
        });
      }

      // Drag and drop untuk file upload
      this.setupDragDrop();
    },

    /**
     * Setup drag and drop untuk file upload
     */
    setupDragDrop: function () {
      const uploadContainers = document.querySelectorAll(".file-upload-container");

      uploadContainers.forEach((container) => {
        const inputElement = container.querySelector('input[type="file"]');

        // Prevent default drag behaviors
        ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
          container.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
          e.preventDefault();
          e.stopPropagation();
        }

        // Highlight drop area when dragging over it
        ["dragenter", "dragover"].forEach((eventName) => {
          container.addEventListener(
            eventName,
            () => {
              container.classList.add("border-purple-500", "bg-purple-100");
            },
            false
          );
        });

        // Remove highlight when dragging leaves
        ["dragleave", "drop"].forEach((eventName) => {
          container.addEventListener(
            eventName,
            () => {
              container.classList.remove("border-purple-500", "bg-purple-100");
            },
            false
          );
        });

        // Handle dropped files
        container.addEventListener(
          "drop",
          (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;

            if (files.length > 0) {
              inputElement.files = files;
              const event = new Event("change", { bubbles: true });
              inputElement.dispatchEvent(event);
            }
          },
          false
        );
      });
    },

    /**
     * Setup handlers for data export buttons
     */
    setupExportHandlers: function() {
      // Export CSV button
      const exportCsvBtn = document.getElementById("btn-export-csv");
      if (exportCsvBtn) {
        exportCsvBtn.addEventListener("click", () => {
          this.handleExportData("csv");
        });
      }

      // Export Excel button
      const exportExcelBtn = document.getElementById("btn-export-excel");
      if (exportExcelBtn) {
        exportExcelBtn.addEventListener("click", () => {
          this.handleExportData("excel");
        });
      }

      // Export PDF button
      const exportPdfBtn = document.getElementById("btn-export-pdf");
      if (exportPdfBtn) {
        exportPdfBtn.addEventListener("click", () => {
          this.handleExportData("pdf");
        });
      }
    },

    /**
     * Setup handlers for backup & restore
     */
    setupBackupHandlers: function() {
      // Backup button
      const backupBtn = document.getElementById("btn-backup");
      if (backupBtn) {
        backupBtn.addEventListener("click", () => {
          this.handleBackup();
        });
      }

      // Restore form
      const restoreForm = document.getElementById("form-restore");
      if (restoreForm) {
        restoreForm.addEventListener("submit", (e) => {
          // Form will submit normally, validation is handled by the handleImportSubmit equivalent
        });
      }
    },

    /**
     * Handle exporting data to different formats
     * @param {string} format - Format to export (csv, excel, pdf)
     */
    handleExportData: function(format) {
      const resultId = document.getElementById("export-result-id").value;
      
      if (!resultId) {
        Klasterisasi.utils.showErrorMessage("Silakan pilih hasil klasterisasi yang akan diekspor");
        return;
      }
      
      // Create export URL based on format
      let url = "";
      switch (format) {
        case "csv":
          url = `/klasterisasi/export/csv/${resultId}`;
          break;
        case "excel":
          url = `/klasterisasi/export/excel/${resultId}`;
          break;
        case "pdf":
          url = `/klasterisasi/export/pdf/${resultId}`;
          break;
        default:
          Klasterisasi.utils.showErrorMessage("Format ekspor tidak valid");
          return;
      }
      
      // Redirect to download URL
      window.location.href = url;
    },

    /**
     * Handle backup data to ZIP file
     */
    handleBackup: function() {
      const resultId = document.getElementById("export-result-id").value;
      
      if (!resultId) {
        Klasterisasi.utils.showErrorMessage("Silakan pilih hasil klasterisasi yang akan di-backup");
        return;
      }
      
      // Redirect to backup endpoint
      window.location.href = `/klasterisasi/backup/${resultId}`;
    },

    /**
     * Handle file upload untuk hasil klasterisasi
     * @param {Event} e - Event change dari file input
     */
    handleClusterFileUpload: function(e) {
      const file = e.target.files[0];
      if (!file) return;

      // Validate file type
      if (file.type !== "text/csv" && !file.name.endsWith(".csv")) {
        this.showFileError("Hanya file CSV yang diperbolehkan.");
        e.target.value = "";
        return;
      }

      // Display file info
      const fileInfo = document.getElementById("cluster-file-info");
      const fileName = document.getElementById("cluster-file-name");
      const fileSize = document.getElementById("cluster-file-size");

      if (fileInfo && fileName && fileSize) {
        fileInfo.classList.remove("hidden");
        fileName.textContent = file.name;
        fileSize.textContent = this.formatFileSize(file.size);

        // Create FormData for API call
        const formData = new FormData();
        formData.append("csv_file", file);  // Pastikan parameter ini sesuai dengan yang diharapkan server

        // Show loading
        document.getElementById("csv-preview").classList.remove("hidden");
        document.getElementById("csv-preview-header").innerHTML = "";
        document.getElementById("csv-preview-content").innerHTML = 
          '<tr><td colspan="10" class="text-center py-3">Memuat data...</td></tr>';

        // Call API to preview CSV
        fetch(Klasterisasi.API.PREVIEW_CSV, {
          method: "POST",
          body: formData,
        })
          .then((response) => {
            if (!response.ok) {
              throw new Error("Network response was not ok");
            }
            return response.json();
          })
          .then((data) => {
            // Render preview table
            this.renderPreviewTable(data);
          })
          .catch((error) => {
            console.error("Error previewing CSV:", error);
            document.getElementById("csv-preview-content").innerHTML = 
              `<tr><td colspan="10" class="text-center py-3 text-red-600">Gagal memuat preview: ${error.message}</td></tr>`;
          });
      }
    },

    /**
     * Handle file upload untuk data sekolah
     * @param {Event} e - Event change dari file input
     */
    handleSekolahFileUpload: function(e) {
      const file = e.target.files[0];
      if (!file) return;

      // Validate file type
      if (file.type !== "text/csv" && !file.name.endsWith(".csv")) {
        this.showFileError("Hanya file CSV yang diperbolehkan.");
        e.target.value = "";
        return;
      }

      // Display file info
      const fileInfo = document.getElementById("sekolah-file-info");
      const fileName = document.getElementById("sekolah-file-name");
      const fileSize = document.getElementById("sekolah-file-size");

      if (fileInfo && fileName && fileSize) {
        fileInfo.classList.remove("hidden");
        fileName.textContent = file.name;
        fileSize.textContent = this.formatFileSize(file.size);

        // Preview CSV
        this.previewCSV(
          file,
          "sekolah-csv-preview",
          "sekolah-csv-preview-header",
          "sekolah-csv-preview-content",
          "sekolah-validation-message"
        );
      }
    },

    /**
     * Format file size untuk tampilan yang lebih user-friendly
     * @param {number} bytes - Ukuran file dalam bytes
     * @returns {string} - Ukuran file yang diformat
     */
    formatFileSize: function(bytes) {
      if (bytes === 0) return "0 Bytes";

      const k = 1024;
      const sizes = ["Bytes", "KB", "MB", "GB"];
      const i = Math.floor(Math.log(bytes) / Math.log(k));

      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
    },

    /**
     * Render preview table hasil CSV
     * @param {Object} data - Data hasil preview dari server
     */
    renderPreviewTable: function(data) {
      const headerElement = document.getElementById("csv-preview-header");
      const contentElement = document.getElementById("csv-preview-content");
      const validationElement = document.getElementById("csv-validation-message");
      
      if (!headerElement || !contentElement || !validationElement) return;
      
      // Handle validation messages
      if (data.error || (data.missing_columns && data.missing_columns.length > 0)) {
        validationElement.classList.remove("hidden");
        validationElement.classList.add("text-red-600", "bg-red-100", "p-2", "rounded");
        validationElement.textContent = data.error || 
          `Kolom yang diperlukan tidak ditemukan: ${data.missing_columns.join(", ")}`;
      } else {
        validationElement.classList.add("hidden");
      }
      
      // Clear previous content
      headerElement.innerHTML = "";
      contentElement.innerHTML = "";
      
      if (data.preview && data.columns) {
        // Create header row
        const headerRow = document.createElement("tr");
        data.columns.forEach((column) => {
          const th = document.createElement("th");
          th.className = "px-4 py-2 text-xs border-b";
          th.textContent = column;
          headerRow.appendChild(th);
        });
        headerElement.appendChild(headerRow);
        
        // Create rows for preview data
        data.preview.forEach((row) => {
          const tr = document.createElement("tr");
          tr.className = "hover:bg-gray-50";
          
          data.columns.forEach((column) => {
            const td = document.createElement("td");
            td.className = "px-4 py-2 text-xs border-b";
            td.textContent = row[column] !== null && row[column] !== undefined ? row[column] : "";
            tr.appendChild(td);
          });
          
          contentElement.appendChild(tr);
        });
        
        // Show stats
        const preview = document.getElementById("csv-preview");
        if (preview) {
          const existingStats = preview.querySelector(".preview-stats");
          if (existingStats) existingStats.remove();
          
          const statsHtml = `
            <div class="mt-3 pt-3 border-t border-gray-200 text-xs preview-stats">
              <p class="font-medium">Total: ${data.row_count || "?"} baris, ${data.columns.length} kolom</p>
              ${data.clusters ? `<p>Jumlah cluster: ${data.clusters}</p>` : ''}
            </div>
          `;
          preview.insertAdjacentHTML("beforeend", statsHtml);
        }
      }
    },

    /**
     * Preview file CSV sebelum upload
     * @param {File} file - File CSV yang akan di-preview
     * @param {string} previewId - ID container preview
     * @param {string} headerId - ID header tabel
     * @param {string} contentId - ID content tabel
     * @param {string} validationId - ID message validasi
     */
    previewCSV: function(file, previewId, headerId, contentId, validationId) {
      const preview = document.getElementById(previewId);
      const headerElement = document.getElementById(headerId);
      const contentElement = document.getElementById(contentId);
      const validationElement = document.getElementById(validationId);

      if (!preview || !headerElement || !contentElement || !validationElement) return;

      // Create FormData for API call
      const formData = new FormData();
      formData.append("csv_file", file);

      // Show loading
      preview.classList.remove("hidden");
      headerElement.innerHTML = "";
      contentElement.innerHTML = '<tr><td colspan="10" class="text-center py-3">Memuat data...</td></tr>';

      // Call API to preview CSV
      fetch(Klasterisasi.API.PREVIEW_CSV, {
        method: "POST",
        body: formData,
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.json();
        })
        .then((data) => {
          this.renderPreviewTable({
            ...data,
            columns: data.columns || [],
            preview: data.preview || []
          });
        })
        .catch((error) => {
          console.error("Error previewing CSV:", error);
          contentElement.innerHTML = `<tr><td colspan="10" class="text-center py-3 text-red-600">Gagal memuat preview: ${error.message}</td></tr>`;
        });
    },

    /**
     * Show file error message
     * @param {string} message - Error message to display
     */
    showFileError: function(message) {
      const errors = document.querySelectorAll(".file-error");

      // Remove existing error messages
      errors.forEach((error) => error.remove());

      // Create new error message
      const errorDiv = document.createElement("div");
      errorDiv.className = "file-error bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mt-2";
      errorDiv.innerHTML = `
        <span class="block sm:inline">${message}</span>
        <button type="button" class="absolute top-0 bottom-0 right-0 px-4 py-3">
          <svg class="fill-current h-6 w-6 text-red-500" role="button" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
            <title>Close</title>
            <path d="M14.348 14.849a1.2 1.2 0 0 1-1.697 0L10 11.819l-2.651 3.029a1.2 1.2 0 1 1-1.697-1.697l2.758-3.15-2.759-3.152a1.2 1.2 0 1 1 1.697-1.697L10 8.183l2.651-3.031a1.2 1.2 0 1 1 1.697 1.697l-2.758 3.152 2.758 3.15a1.2 1.2 0 0 1 0 1.698z"/>
          </svg>
        </button>
      `;

      // Add click event to close button
      const closeButton = errorDiv.querySelector("button");
      closeButton.addEventListener("click", () => {
        errorDiv.remove();
      });

      // Find the file upload container to append error to
      const fileContainer = document.querySelector(".file-upload-container");
      if (fileContainer) {
        fileContainer.parentNode.insertBefore(errorDiv, fileContainer.nextSibling);
      }
    },

    /**
     * Handle form submission untuk import hasil klasterisasi
     * @param {Event} e - Event submit dari form
     */
    handleImportSubmit: function(e) {
      const fileInput = document.getElementById("cluster-file-upload");
      const submitButton = document.getElementById("btn-import-klasterisasi");
      const buttonText = submitButton.querySelector(".btn-text");
      const loadingSpinner = submitButton.querySelector(".loading-spinner");

      // Validate file
      if (!fileInput || !fileInput.files.length) {
        e.preventDefault();
        this.showFileError("Silakan pilih file CSV terlebih dahulu.");
        return;
      }

      // Show loading state
      if (submitButton && buttonText && loadingSpinner) {
        buttonText.textContent = "Mengimpor Data...";
        loadingSpinner.classList.remove("hidden");
        submitButton.disabled = true;
      }

      // Form akan di-submit secara normal, tidak perlu AJAX
    },

    /**
     * Handle form submission untuk import data sekolah
     * @param {Event} e - Event submit dari form
     */
    handleImportSekolahSubmit: function(e) {
      const fileInput = document.getElementById("sekolah-file-upload");
      const resultSelect = document.getElementById("result_id");
      const submitButton = document.getElementById("btn-import-sekolah");
      const buttonText = submitButton.querySelector(".btn-text");
      const loadingSpinner = submitButton.querySelector(".loading-spinner");

      // Validate
      if (!fileInput || !fileInput.files.length) {
        e.preventDefault();
        Klasterisasi.utils.showErrorMessage("Silakan pilih file CSV terlebih dahulu.");
        return;
      }

      if (!resultSelect || !resultSelect.value) {
        e.preventDefault();
        Klasterisasi.utils.showErrorMessage("Silakan pilih hasil klasterisasi yang akan dilengkapi.");
        return;
      }

      // Show loading state
      if (submitButton && buttonText && loadingSpinner) {
        buttonText.textContent = "Mengimpor Data Sekolah...";
        loadingSpinner.classList.remove("hidden");
        submitButton.disabled = true;
      }

      // Form akan di-submit secara normal, tidak perlu AJAX
    }
  },

  /**
   * Module untuk tab Hasil Klasterisasi
   */
  hasilModule: {
    /**
     * Setup event listeners untuk tab Hasil Klasterisasi
     */
    setupEventListeners: function() {
      // Filter form
      const filterForm = document.getElementById("hasil-filter-form");
      if (filterForm) {
        filterForm.addEventListener("submit", (e) => {
          e.preventDefault();
          this.applyFilters();
        });
      }

      // Refresh button
      const refreshBtn = document.getElementById("refresh-results");
      if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
          this.loadResults(true);
        });
      }

      // Setup quality check and optimization handlers
      this.setupQualityHandlers();

      // Setup comparison handlers
      this.setupComparisonHandlers();
    },

    /**
     * Setup event handlers for quality check and optimization
     */
    setupQualityHandlers: function() {
      // Check quality button
      const checkQualityBtn = document.getElementById("btn-check-quality");
      if (checkQualityBtn) {
        checkQualityBtn.addEventListener("click", () => {
          const resultId = document.getElementById("quality-result-id").value;
          if (resultId) {
            this.checkDataQuality(resultId);
          } else {
            Klasterisasi.utils.showErrorMessage("Silakan pilih hasil klasterisasi terlebih dahulu");
          }
        });
      }

      // Fix issues button
      const fixIssuesBtn = document.getElementById("btn-fix-issues");
      if (fixIssuesBtn) {
        fixIssuesBtn.addEventListener("click", () => {
          const resultId = document.getElementById("quality-result-id").value;
          if (resultId) {
            this.fixDataIssues(resultId);
          } else {
            Klasterisasi.utils.showErrorMessage("Silakan pilih hasil klasterisasi terlebih dahulu");
          }
        });
      }

      // Optimize button
      const optimizeBtn = document.getElementById("btn-optimize");
      if (optimizeBtn) {
        optimizeBtn.addEventListener("click", () => {
          const resultId = document.getElementById("quality-result-id").value;
          if (resultId) {
            this.optimizeClusteringData(resultId);
          } else {
            Klasterisasi.utils.showErrorMessage("Silakan pilih hasil klasterisasi terlebih dahulu");
          }
        });
      }

      // Issue toggle buttons
      document.addEventListener("click", (e) => {
        if (e.target.closest(".issue-toggle")) {
          const toggle = e.target.closest(".issue-toggle");
          const targetId = toggle.getAttribute("data-target");
          const content = document.getElementById(targetId);
          const icon = toggle.querySelector("svg");
          
          if (content && icon) {
            content.classList.toggle("hidden");
            icon.classList.toggle("rotate-180");
          }
        }
      });
    },

    /**
     * Setup comparison handlers
     */
    setupComparisonHandlers: function() {
      // Compare button
      const compareBtn = document.getElementById("btn-compare");
      if (compareBtn) {
        compareBtn.addEventListener("click", () => {
          const checkedBoxes = document.querySelectorAll('input[name="compare_results"]:checked');
          const resultIds = Array.from(checkedBoxes).map(cb => cb.value);
          
          if (resultIds.length < 2) {
            Klasterisasi.utils.showErrorMessage("Pilih minimal 2 hasil klasterisasi untuk dibandingkan");
            return;
          }
          
          this.compareResults(resultIds);
        });
      }
    },

    /**
     * Load hasil klasterisasi dari API
     * @param {boolean} forceRefresh - Paksa refresh data dari server
     */
    loadResults: function(forceRefresh = false) {
      const loadingElement = document.getElementById("results-loading");
      const emptyState = document.getElementById("results-empty-state");
      const resultsContainer = document.getElementById("results-cards-container");

      if (!loadingElement || !emptyState || !resultsContainer) return;

      // Show loading state
      loadingElement.classList.remove("hidden");
      emptyState.classList.add("hidden");
      resultsContainer.classList.add("hidden");

      Klasterisasi.state.loadingStates.results = true;

      // Use cached data if available and not force refresh
      if (Klasterisasi.state.data.results.length > 0 && !forceRefresh) {
        this.renderResults(Klasterisasi.state.data.results);
        return;
      }

      // Fetch new data
      Klasterisasi.fetchResults()
        .then((results) => {
          Klasterisasi.state.data.results = results;
          this.renderResults(results);
          Klasterisasi.updateDashboardStats();
          this.updateComparisonCheckboxes(results);
        })
        .catch((error) => {
          console.error("Error loading results:", error);
          loadingElement.classList.add("hidden");
          Klasterisasi.utils.showErrorMessage("Gagal memuat hasil klasterisasi. Silahkan coba lagi.");
          Klasterisasi.state.loadingStates.results = false;
        });
    },

    /**
     * Update comparison checkboxes based on available results
     * @param {Array} results - Array of clustering results
     */
    updateComparisonCheckboxes: function(results) {
      const container = document.getElementById("comparison-checkboxes");
      if (!container) return;

      // Clear previous content
      container.innerHTML = "";

      // Only show completed results
      const completedResults = results.filter(r => r.status === "completed");
      
      if (completedResults.length === 0) {
        container.innerHTML = '<p class="text-gray-500">Tidak ada hasil klasterisasi yang tersedia untuk dibandingkan.</p>';
        return;
      }

      // Add checkbox for each result
      completedResults.forEach(result => {
        const checkbox = document.createElement("div");
        checkbox.className = "flex items-center space-x-2";
        checkbox.innerHTML = `
          <input type="checkbox" id="compare_${result.id}" name="compare_results" value="${result.id}"
              class="w-4 h-4 text-purple-600 rounded focus:ring-purple-500">
          <label for="compare_${result.id}" class="text-sm text-gray-700">
              ${result.jenjang} - ${result.skenario == "1" ? "Dengan Outlier" : "Tanpa Outlier"} (${result.jumlah_cluster} klaster)
          </label>
        `;
        container.appendChild(checkbox);
      });
    },

    /**
     * Render hasil klasterisasi ke UI
     * @param {Array} results - Array hasil klasterisasi dari API
     */
    renderResults: function(results) {
      const loadingElement = document.getElementById("results-loading");
      const emptyState = document.getElementById("results-empty-state");
      const resultsContainer = document.getElementById("results-cards-container");

      // Hide loading
      if (loadingElement) {
        loadingElement.classList.add("hidden");
      }

      // Show empty state if no results
      if (results.length === 0) {
        if (emptyState) emptyState.classList.remove("hidden");
        if (resultsContainer) resultsContainer.classList.add("hidden");
        Klasterisasi.state.loadingStates.results = false;
        return;
      }

      // Prepare UI
      if (emptyState) emptyState.classList.add("hidden");
      if (resultsContainer) {
        resultsContainer.classList.remove("hidden");
        resultsContainer.innerHTML = "";

        // Apply current filters before rendering
        const filteredResults = this.filterResults(results);

        // Render each result card
        filteredResults.forEach((result) => {
          const cardHtml = this.generateResultCard(result);
          resultsContainer.insertAdjacentHTML("beforeend", cardHtml);
        });

        // Add event listeners for the newly created cards
        this.setupCardEventListeners();
      }

      Klasterisasi.state.loadingStates.results = false;
    },

    /**
     * Generate HTML untuk card hasil klasterisasi
     * @param {Object} result - Data hasil klasterisasi
     * @returns {string} - HTML string untuk card
     */
    generateResultCard: function(result) {
      const jenjangColor = result.jenjang === "SMA" ? "purple" : "green";
      const status = result.status;
      const statusClass = status === "completed"
        ? "bg-green-100 text-green-800"
        : status === "processing"
        ? "bg-yellow-100 text-yellow-800"
        : "bg-red-100 text-red-800";

      const importedDate = new Date(result.imported_at);
      const formattedDate = `${importedDate.toLocaleDateString("id-ID")} ${importedDate.toLocaleTimeString("id-ID", {
        hour: "2-digit",
        minute: "2-digit",
      })}`;

      return `
        <div class="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden hover:shadow-lg transition-all">
          <div class="p-4 bg-${jenjangColor}-500 text-white">
            <div class="flex justify-between items-center">
              <h3 class="font-bold">${result.jenjang} - ${result.skenario === "1" ? "Dengan Outlier" : "Tanpa Outlier"}</h3>
              <span class="bg-white text-${jenjangColor}-600 text-xs px-2 py-1 rounded font-semibold">${result.jumlah_cluster} klaster</span>
            </div>
          </div>
          <div class="p-4">
            <div class="mb-3">
              <p class="text-sm text-gray-600">ID: ${result.id}</p>
              <p class="text-sm text-gray-600">Jumlah Kecamatan: ${result.kecamatan_count || "0"}</p>
              <p class="text-sm text-gray-600">Tanggal: ${formattedDate}</p>
              ${result.description ? `<p class="text-sm text-gray-600 mt-2 italic">"${result.description}"</p>` : ""}
            </div>

            <div class="mt-2">
              <span class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${statusClass}">
                ${result.status}
              </span>
            </div>

            <div class="mt-4 flex space-x-2 justify-end">
              <a href="#" class="text-indigo-600 hover:text-indigo-900 view-result-btn" data-result-id="${result.id}">Lihat</a>
              ${result.status === "completed" ? `
                <div class="relative export-menu-container">
                  <button type="button" class="text-green-600 hover:text-green-900 export-btn" data-result-id="${result.id}">Export</button>
                  <div class="export-menu hidden absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg z-10 py-1">
                    <a href="/klasterisasi/export/csv/${result.id}" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Export CSV</a>
                    <a href="/klasterisasi/export/excel/${result.id}" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Export Excel</a>
                    <a href="/klasterisasi/export/pdf/${result.id}" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">Export PDF</a>
                  </div>
                </div>
                <a href="#" class="text-red-600 hover:text-red-900 delete-result-btn" data-result-id="${result.id}">Hapus</a>
              ` : ""}
            </div>
          </div>
        </div>
      `;
    },

    /**
     * Setup event listeners untuk card hasil klasterisasi
     */
    setupCardEventListeners: function() {
      // View result details button
      document.querySelectorAll(".view-result-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          const resultId = btn.getAttribute("data-result-id");
          if (resultId) {
            // Switch to karakteristik tab and load data for this result
            Klasterisasi.switchTab("karakteristik-content", document.getElementById("karakteristik-tab"));
            document.getElementById("karakteristik-result-id").value = resultId;
            // Trigger change event to load clusters
            const event = new Event("change");
            document.getElementById("karakteristik-result-id").dispatchEvent(event);
          }
        });
      });

      // Export dropdown toggle
      document.querySelectorAll(".export-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          e.stopPropagation();

          // Close all other export menus
          document.querySelectorAll(".export-menu").forEach((menu) => {
            if (menu !== btn.nextElementSibling) {
              menu.classList.add("hidden");
            }
          });

          // Toggle this menu
          const menu = btn.nextElementSibling;
          menu.classList.toggle("hidden");
        });
      });

      // Close export menus when clicking elsewhere
      document.addEventListener("click", (e) => {
        if (!e.target.closest(".export-menu-container")) {
          document.querySelectorAll(".export-menu").forEach((menu) => {
            menu.classList.add("hidden");
          });
        }
      });

      // Delete result button
      document.querySelectorAll(".delete-result-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          const resultId = btn.getAttribute("data-result-id");
          if (resultId) {
            this.confirmDeleteResult(resultId);
          }
        });
      });
    },

    /**
     * Show confirmation dialog untuk delete hasil klasterisasi
     * @param {string} resultId - ID hasil yang akan dihapus
     */
    confirmDeleteResult: function(resultId) {
      const deleteIdInput = document.getElementById("delete-result-id");
      if (deleteIdInput) {
        deleteIdInput.value = resultId;
      }

      const confirmBtn = document.getElementById("confirm-delete-btn");
      if (confirmBtn) {
        // Remove existing event listeners
        const newBtn = confirmBtn.cloneNode(true);
        confirmBtn.parentNode.replaceChild(newBtn, confirmBtn);

        // Add new event listener
        newBtn.addEventListener("click", () => {
          this.deleteResult(resultId);
        });
      }

      Klasterisasi.openModal("delete-confirmation-modal");
    },

    /**
     * Delete hasil klasterisasi
     * @param {string} resultId - ID hasil yang akan dihapus
     */
    deleteResult: function(resultId) {
      const confirmBtn = document.getElementById("confirm-delete-btn");
      if (confirmBtn) {
        confirmBtn.innerHTML = `
          <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Menghapus...
        `;
        confirmBtn.disabled = true;
      }

      fetch(`${Klasterisasi.API.DELETE_RESULT}${resultId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.json();
        })
        .then((data) => {
          if (data.success) {
            // Close modal
            Klasterisasi.closeModal("delete-confirmation-modal");

            // Remove result from state
            Klasterisasi.state.data.results = Klasterisasi.state.data.results.filter(
              (r) => r.id !== parseInt(resultId)
            );

            // Refresh the results list
            this.renderResults(Klasterisasi.state.data.results);

            // Update dashboard stats
            Klasterisasi.updateDashboardStats();

            // Show success message
            Klasterisasi.utils.showSuccessMessage(data.message || "Hasil klasterisasi berhasil dihapus.");
          } else {
            throw new Error(data.message || "Gagal menghapus hasil klasterisasi.");
          }
        })
        .catch((error) => {
          console.error("Error deleting result:", error);
          Klasterisasi.utils.showErrorMessage(error.message);

          // Reset button
          if (confirmBtn) {
            confirmBtn.innerHTML = "Hapus";
            confirmBtn.disabled = false;
          }
        });
    },

    /**
     * Check data quality for a clustering result
     * @param {string} resultId - ID hasil klasterisasi
     */
    checkDataQuality: function(resultId) {
      const resultsElement = document.getElementById("quality-check-results");
      const checkQualityBtn = document.getElementById("btn-check-quality");
      
      if (checkQualityBtn) {
        checkQualityBtn.disabled = true;
        checkQualityBtn.innerHTML = `
          <svg class="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Memeriksa...
        `;
      }

      fetch(`${Klasterisasi.API.CHECK_QUALITY}${resultId}`)
        .then((response) => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.json();
        })
        .then((data) => {
          if (resultsElement) {
            resultsElement.classList.remove("hidden");
            
            // Update issue counts
            document.getElementById("total-issues").textContent = data.total_issues || 0;
            document.getElementById("missing-medoids-count").textContent = (data.missing_medoids || []).length;
            document.getElementById("multiple-medoids-count").textContent = (data.multiple_medoids || []).length;
            document.getElementById("outlier-count").textContent = (data.outliers || []).length;
            document.getElementById("inconsistent-count").textContent = (data.inconsistencies || []).length;
            
            // Update issue details
            this.updateIssueList("missing-medoids-list", data.missing_medoids || []);
            this.updateIssueList("multiple-medoids-list", data.multiple_medoids || []);
            this.updateIssueList("outliers-list", data.outliers || []);
            this.updateIssueList("inconsistencies-list", data.inconsistencies || []);
            
            // Enable/disable fix button based on issues found
            const fixButton = document.getElementById("btn-fix-issues");
            if (fixButton) {
              fixButton.disabled = data.total_issues === 0;
            }
          }
        })
        .catch((error) => {
          console.error("Error checking quality:", error);
          Klasterisasi.utils.showErrorMessage(`Gagal memeriksa kualitas data: ${error.message}`);
        })
        .finally(() => {
          if (checkQualityBtn) {
            checkQualityBtn.disabled = false;
            checkQualityBtn.innerHTML = `
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
              Periksa Kualitas Data
            `;
          }
        });
    },

    /**
     * Update issue list with found issues
     * @param {string} listId - ID of list element
     * @param {Array} issues - Array of issues
     */
    updateIssueList: function(listId, issues) {
      const list = document.getElementById(listId);
      if (!list) return;
      
      list.innerHTML = "";
      
      if (issues.length === 0) {
        list.innerHTML = "<li class='text-gray-500'>Tidak ada masalah terdeteksi</li>";
        return;
      }
      
      issues.forEach(issue => {
        const li = document.createElement("li");
        li.textContent = typeof issue === 'object' ? JSON.stringify(issue) : issue;
        list.appendChild(li);
      });
    },

    /**
     * Fix data quality issues for a clustering result
     * @param {string} resultId - ID hasil klasterisasi
     */
    fixDataIssues: function(resultId) {
      const fixBtn = document.getElementById("btn-fix-issues");
      
      if (fixBtn) {
        fixBtn.disabled = true;
        fixBtn.innerHTML = `
          <svg class="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Memperbaiki...
        `;
      }

      fetch(`${Klasterisasi.API.FIX_ISSUES}${resultId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.json();
        })
        .then((data) => {
          if (data.success) {
            Klasterisasi.utils.showSuccessMessage(data.message || "Masalah berhasil diperbaiki.");
            // Re-check quality to update UI
            this.checkDataQuality(resultId);
          } else {
            throw new Error(data.message || "Gagal memperbaiki masalah kualitas data.");
          }
        })
        .catch((error) => {
          console.error("Error fixing issues:", error);
          Klasterisasi.utils.showErrorMessage(`Gagal memperbaiki masalah: ${error.message}`);
        })
        .finally(() => {
          if (fixBtn) {
            fixBtn.disabled = false;
            fixBtn.innerHTML = `
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path>
              </svg>
              Perbaiki Semua Masalah
            `;
          }
        });
    },

    /**
     * Optimize clustering data
     * @param {string} resultId - ID hasil klasterisasi
     */
    optimizeClusteringData: function(resultId) {
      const optimizeBtn = document.getElementById("btn-optimize");
      
      if (optimizeBtn) {
        optimizeBtn.disabled = true;
        optimizeBtn.innerHTML = `
          <svg class="animate-spin -ml-1 mr-2 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Mengoptimalkan...
        `;
      }

      fetch(`${Klasterisasi.API.OPTIMIZE}${resultId}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.json();
        })
        .then((data) => {
          if (data.success) {
            Klasterisasi.utils.showSuccessMessage(data.message || "Data berhasil dioptimalkan.");
            // Re-check quality to update UI
            this.checkDataQuality(resultId);
          } else {
            throw new Error(data.message || "Gagal mengoptimalkan data klasterisasi.");
          }
        })
        .catch((error) => {
          console.error("Error optimizing data:", error);
          Klasterisasi.utils.showErrorMessage(`Gagal mengoptimalkan data: ${error.message}`);
        })
        .finally(() => {
          if (optimizeBtn) {
            optimizeBtn.disabled = false;
            optimizeBtn.innerHTML = `
              <svg class="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              </svg>
              Optimasi Data Klaster
            `;
          }
        });
    },

    /**
     * Compare multiple clustering results
     * @param {Array} resultIds - Array of result IDs to compare
     */
    compareResults: function(resultIds) {
      // Construct URL with query parameters
      let url = '/klasterisasi/compare?';
      resultIds.forEach(id => {
        url += `ids=${id}&`;
      });
      
      // Remove trailing & and redirect
      window.location.href = url.slice(0, -1);
    },

    /**
     * Apply filters pada hasil klasterisasi
     */
    applyFilters: function() {
      this.renderResults(Klasterisasi.state.data.results);
    },

    /**
     * Filter hasil klasterisasi berdasarkan filter yang dipilih
     * @param {Array} results - Array hasil klasterisasi
     * @returns {Array} - Array hasil klasterisasi yang sudah difilter
     */
    filterResults: function(results) {
      const jenjangFilter = document.getElementById("filter-jenjang").value;
      const skenarioFilter = document.getElementById("filter-skenario").value;
      const clusterFilter = document.getElementById("filter-jumlah-cluster").value;
      const sortBy = document.getElementById("filter-sort").value;

      // Apply filters
      let filtered = [...results];

      if (jenjangFilter) {
        filtered = filtered.filter((r) => r.jenjang === jenjangFilter);
      }

      if (skenarioFilter) {
        filtered = filtered.filter((r) => r.skenario === skenarioFilter);
      }

      if (clusterFilter) {
        filtered = filtered.filter((r) => r.jumlah_cluster === parseInt(clusterFilter));
      }

      // Apply sorting
      filtered.sort((a, b) => {
        switch (sortBy) {
          case "newest":
            return new Date(b.imported_at) - new Date(a.imported_at);
          case "oldest":
            return new Date(a.imported_at) - new Date(b.imported_at);
          case "jenjang":
            return a.jenjang.localeCompare(b.jenjang) || b.skenario - a.skenario;
          case "cluster":
            return b.jumlah_cluster - a.jumlah_cluster;
          default:
            return new Date(b.imported_at) - new Date(a.imported_at);
        }
      });

      return filtered;
    },
  },

  /**
   * Module untuk tab Analisis Karakteristik
   */
  karakteristikModule: {
    /**
     * Setup event listeners untuk tab Analisis Karakteristik
     */
    setupEventListeners: function() {
      // Result selection change
      const resultSelect = document.getElementById("karakteristik-result-id");
      if (resultSelect) {
        resultSelect.addEventListener("change", () => {
          this.loadClustersForResult(resultSelect.value);
        });
      }

      // Cluster selection change
      const clusterSelect = document.getElementById("karakteristik-cluster");
      if (clusterSelect) {
        clusterSelect.addEventListener("change", () => {
          Klasterisasi.state.data.selectedCluster = clusterSelect.value;
        });
      }

      // Filter form submit
      const filterForm = document.getElementById("karakteristik-filter-form");
      if (filterForm) {
        filterForm.addEventListener("submit", (e) => {
          e.preventDefault();
          this.loadCharacteristics();
        });
      }

      // View toggle buttons
      const cardViewBtn = document.getElementById("card-view-btn");
      const tableViewBtn = document.getElementById("table-view-btn");

      if (cardViewBtn) {
        cardViewBtn.addEventListener("click", () => {
          this.switchView("card");
        });
      }

      if (tableViewBtn) {
        tableViewBtn.addEventListener("click", () => {
          this.switchView("table");
        });
      }
    },

    /**
     * Inisialisasi filter options untuk tab Analisis Karakteristik
     */
    initFilterOptions: function() {
      // Fill result select box if empty
      const resultSelect = document.getElementById("karakteristik-result-id");

      if (resultSelect && resultSelect.options.length <= 1) {
        // Already loaded in the template by Jinja
        // Add event to trigger the first load if a result is selected
        if (resultSelect.value) {
          this.loadClustersForResult(resultSelect.value);
        }
      }
    },

    /**
     * Load cluster options for the selected result
     * @param {string} resultId - ID hasil klasterisasi yang dipilih
     */
    loadClustersForResult: function(resultId) {
      if (!resultId) return;

      const clusterSelect = document.getElementById("karakteristik-cluster");
      if (!clusterSelect) return;

      // Set the selected result in state
      Klasterisasi.state.data.selectedResult = resultId;

      // Clear current options except the first one
      while (clusterSelect.options.length > 1) {
        clusterSelect.remove(1);
      }

      // Add loading option
      const loadingOption = document.createElement("option");
      loadingOption.text = "Memuat klaster...";
      loadingOption.disabled = true;
      clusterSelect.add(loadingOption);
      clusterSelect.selectedIndex = clusterSelect.options.length - 1;

      // Fetch clusters for this result
      fetch(`${Klasterisasi.API.CLUSTERS}${resultId}`)
        .then((response) => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.json();
        })
        .then((data) => {
          // Remove loading option
          clusterSelect.remove(clusterSelect.options.length - 1);

          // Add cluster options
          if (data.clusters) {
            const clusters = Object.keys(data.clusters).sort((a, b) => parseInt(a) - parseInt(b));

            clusters.forEach((cluster) => {
              const option = document.createElement("option");
              option.value = cluster;
              option.text = `Klaster ${cluster} (${data.clusters[cluster]} kecamatan)`;
              clusterSelect.add(option);
            });
          }

          // Reset to "Semua Klaster"
          clusterSelect.selectedIndex = 0;
        })
        .catch((error) => {
          console.error("Error loading clusters:", error);
          // Remove loading option
          clusterSelect.remove(clusterSelect.options.length - 1);

          // Add error option
          const errorOption = document.createElement("option");
          errorOption.text = "Error memuat klaster";
          errorOption.disabled = true;
          clusterSelect.add(errorOption);
        });
    },

    /**
     * Load cluster characteristics based on selected filters
     */
    loadCharacteristics: function() {
      const resultId = document.getElementById("karakteristik-result-id").value;
      const cluster = document.getElementById("karakteristik-cluster").value;

      if (!resultId) {
        Klasterisasi.utils.showErrorMessage("Silakan pilih hasil klasterisasi terlebih dahulu.");
        return;
      }

      // Show loading
      const loadingElement = document.getElementById("karakteristik-loading");
      const emptyState = document.getElementById("karakteristik-empty-state");
      const cardView = document.getElementById("karakteristik-card-view");
      const tableView = document.getElementById("karakteristik-table-view");

      if (loadingElement) loadingElement.classList.remove("hidden");
      if (emptyState) emptyState.classList.add("hidden");
      if (cardView) cardView.classList.add("hidden");
      if (tableView) tableView.classList.add("hidden");

      Klasterisasi.state.loadingStates.characteristics = true;

      // Build the API URL with query parameters
      let apiUrl = `${Klasterisasi.API.DETAILED_CHARACTERISTICS}${resultId}`;
      if (cluster) {
        apiUrl += `?cluster=${cluster}`;
      }

      // Fetch characteristics
      fetch(apiUrl)
        .then((response) => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.json();
        })
        .then((data) => {
          // Store in state
          Klasterisasi.state.data.characteristics = data.characteristics || [];

          // Render based on current view
          this.renderCharacteristics();
        })
        .catch((error) => {
          console.error("Error loading characteristics:", error);
          if (loadingElement) loadingElement.classList.add("hidden");

          Klasterisasi.utils.showErrorMessage("Gagal memuat karakteristik klaster. Silakan coba lagi.");
          Klasterisasi.state.loadingStates.characteristics = false;
        });
    },

    /**
     * Render cluster characteristics based on current view (card/table)
     */
    renderCharacteristics: function() {
      const loadingElement = document.getElementById("karakteristik-loading");
      const emptyState = document.getElementById("karakteristik-empty-state");
      const cardView = document.getElementById("karakteristik-card-view");
      const tableView = document.getElementById("karakteristik-table-view");

      // Hide loading
      if (loadingElement) loadingElement.classList.add("hidden");

      const characteristics = Klasterisasi.state.data.characteristics;

      // Show empty state if no data
      if (!characteristics || characteristics.length === 0) {
        if (emptyState) emptyState.classList.remove("hidden");
        if (cardView) cardView.classList.add("hidden");
        if (tableView) tableView.classList.add("hidden");
        Klasterisasi.state.loadingStates.characteristics = false;
        return;
      }

      // Hide empty state
      if (emptyState) emptyState.classList.add("hidden");

      // Render based on current view
      if (Klasterisasi.state.ui.characteristicsView === "card") {
        this.renderCardView(characteristics);
      } else {
        this.renderTableView(characteristics);
      }

      Klasterisasi.state.loadingStates.characteristics = false;
    },

    /**
     * Render characteristics in card view
     * @param {Array} characteristics - Array of cluster characteristics
     */
    renderCardView: function(characteristics) {
      const cardView = document.getElementById("karakteristik-card-view");
      const tableView = document.getElementById("karakteristik-table-view");

      if (!cardView) return;

      // Show card view, hide table view
      cardView.classList.remove("hidden");
      if (tableView) tableView.classList.add("hidden");

      // Clear previous content
      cardView.innerHTML = "";

      // Render each card
      characteristics.forEach((char) => {
        const cardHtml = this.generateCharacteristicCard(char);
        cardView.insertAdjacentHTML("beforeend", cardHtml);
      });

      // Initialize charts for each card
      characteristics.forEach((char) => {
        this.createRadarChart(`cluster-${char.cluster}-chart`, char);
      });
    },

    /**
     * Generate HTML for a characteristic card
     * @param {Object} char - Cluster characteristic data
     * @returns {string} - HTML string for card
     */
    generateCharacteristicCard: function(char) {
      // Map quality level to color
      const qualityColor = this.getQualityColor(char.kualitas_pendidikan);

      // Format percentages consistently with 2 decimal places
      const x5Percent = (char.x5_avg * 100).toFixed(2);
      const x6Percent = (char.x6_avg * 100).toFixed(2);
      const x7Percent = (char.x7_avg * 100).toFixed(2);

      // Determine status for each indicator based on evaluations if available
      const getStatusClass = (indicator) => {
        if (char.evaluations && char.evaluations[indicator]) {
          return char.evaluations[indicator].status === "ideal"
            ? "text-green-600"
            : "text-red-600";
        }
        return "text-gray-800";
      };

      return `
        <div class="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-100 transform transition-all duration-300 hover:shadow-xl hover:-translate-y-1">
          <div class="bg-gradient-to-r from-${qualityColor}-600 to-${qualityColor}-800 p-4 relative">
            <div class="flex justify-between items-center">
              <h3 class="text-lg font-bold text-white">Klaster ${char.cluster}</h3>
              <span class="px-3 py-1 bg-white text-${qualityColor}-700 rounded-full text-xs font-bold">Kualitas ${
        char.kualitas_pendidikan.charAt(0).toUpperCase() + char.kualitas_pendidikan.slice(1)
      }</span>
            </div>
            <p class="text-${qualityColor}-100 text-sm">${char.standar_terpenuhi} dari 7 indikator memenuhi standar ideal</p>

            <!-- Background pattern for card header -->
            <div class="absolute -right-6 -bottom-10 w-32 h-32 bg-${qualityColor}-500 rounded-full opacity-20"></div>
            <div class="absolute right-12 -bottom-4 w-16 h-16 bg-${qualityColor}-400 rounded-full opacity-20"></div>
          </div>

          <div class="p-4">
            <!-- Metrics Grid -->
            <div class="grid grid-cols-3 gap-2 mb-4">
              <div class="bg-${qualityColor}-50 p-2 rounded-lg text-center">
                <span class="text-xs text-${qualityColor}-700 font-medium">Anggota</span>
                <p class="text-${qualityColor}-800 font-bold text-lg">${char.jumlah_anggota}</p>
              </div>
              <div class="bg-${qualityColor}-50 p-2 rounded-lg text-center">
                <span class="text-xs text-${qualityColor}-700 font-medium">Kualitas</span>
                <p class="text-${qualityColor}-800 font-bold text-lg">${
        char.kualitas_pendidikan.charAt(0).toUpperCase() + char.kualitas_pendidikan.slice(1)
      }</p>
              </div>
              <div class="bg-${qualityColor}-50 p-2 rounded-lg text-center">
                <span class="text-xs text-${qualityColor}-700 font-medium">Standar</span>
                <p class="text-${qualityColor}-800 font-bold text-lg">${char.standar_terpenuhi}/7</p>
              </div>
            </div>

            <!-- Radar Chart for indicators -->
            <div class="w-full h-40 bg-gray-50 rounded-lg mb-4 flex items-center justify-center" id="cluster-${
              char.cluster
            }-chart">
              <p class="text-sm text-gray-500">Memuat data indikator...</p>
            </div>

            <!-- Indicator Metrics -->
            <div class="mt-4">
              <h4 class="text-sm font-semibold text-gray-700 mb-2">Nilai Rata-rata Indikator:</h4>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-2">
                <div class="flex justify-between text-xs p-2 bg-gray-50 rounded">
                  <span class="text-gray-600">Rasio Siswa/Kelas (X1):</span>
                  <span class="font-medium ${getStatusClass("x1")}">${char.x1_avg.toFixed(2)}</span>
                </div>
                <div class="flex justify-between text-xs p-2 bg-gray-50 rounded">
                  <span class="text-gray-600">Rasio Siswa/Guru (X2):</span>
                  <span class="font-medium ${getStatusClass("x2")}">${char.x2_avg.toFixed(2)}</span>
                </div>
                <div class="flex justify-between text-xs p-2 bg-gray-50 rounded">
                  <span class="text-gray-600">Rasio Siswa/Rombel (X3):</span>
                  <span class="font-medium ${getStatusClass("x3")}">${char.x3_avg.toFixed(2)}</span>
                </div>
                <div class="flex justify-between text-xs p-2 bg-gray-50 rounded">
                  <span class="text-gray-600">Rombel/Sekolah (X4):</span>
                  <span class="font-medium ${getStatusClass("x4")}">${char.x4_avg.toFixed(2)}</span>
                </div>
                <div class="flex justify-between text-xs p-2 bg-gray-50 rounded">
                  <span class="text-gray-600">Perpustakaan (X5):</span>
                  <span class="font-medium ${getStatusClass("x5")}">${x5Percent}%</span>
                </div>
                <div class="flex justify-between text-xs p-2 bg-gray-50 rounded">
                  <span class="text-gray-600">Laboratorium (X6):</span>
                  <span class="font-medium ${getStatusClass("x6")}">${x6Percent}%</span>
                </div>
                <div class="flex justify-between text-xs p-2 bg-gray-50 rounded md:col-span-2">
                  <span class="text-gray-600">Ruang Kelas (X7):</span>
                  <span class="font-medium ${getStatusClass("x7")}">${x7Percent}%</span>
                </div>
              </div>
            </div>

            <!-- Features section -->
            <div class="mt-4 space-y-2">
              <div>
                <h4 class="text-sm font-semibold text-gray-700">Fitur Unggulan:</h4>
                <p class="text-sm text-green-600">${char.fitur_tinggi || "-"}</p>
              </div>
              <div>
                <h4 class="text-sm font-semibold text-gray-700">Tantangan:</h4>
                <p class="text-sm text-red-600">${char.fitur_rendah || "-"}</p>
              </div>
            </div>

            <!-- Interpretation and Recommendations -->
            <div class="mt-4 border-t border-gray-200 pt-3">
              <h4 class="text-sm font-semibold text-gray-700 mb-1">Interpretasi:</h4>
              <p class="text-sm text-gray-600 mb-2">${char.interpretasi || "Tidak ada data interpretasi."}</p>

              <h4 class="text-sm font-semibold text-gray-700 mb-1">Rekomendasi:</h4>
              <p class="text-sm text-gray-600">${char.rekomendasi || "Tidak ada data rekomendasi."}</p>
            </div>
            
            <!-- Medoid -->
            <div class="mt-4 pt-3 border-t border-gray-200">
              <div class="flex justify-between">
                <span class="text-sm text-gray-500">Medoid:</span>
                <span class="text-sm font-medium text-gray-800">${char.medoid_name || "Tidak ada"}</span>
              </div>
              ${
                char.anggota
                  ? `
                <details class="mt-2">
                  <summary class="text-sm text-${qualityColor}-600 cursor-pointer">Lihat daftar anggota (${
                      char.anggota.length
                    })</summary>
                  <div class="mt-2 p-2 bg-gray-50 rounded-lg text-xs">
                    <ul class="list-disc pl-5 space-y-1">
                      ${char.anggota.map((anggota) => `<li>${anggota}</li>`).join("")}
                    </ul>
                  </div>
                </details>
              `
                  : ""
              }
            </div>
          </div>
        </div>
      `;
    },

    /**
     * Create radar chart for cluster indicators
     * @param {string} containerId - ID of container element
     * @param {Object} data - Cluster characteristic data
     */
    createRadarChart: function(containerId, data) {
      const container = document.getElementById(containerId);
      if (!container) return;

      // Try to load Chart.js dynamically if not available
      if (typeof Chart === "undefined") {
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/chart.js";
        script.onload = () => this.createRadarChartWithData(containerId, data);
        document.head.appendChild(script);
        return;
      }

      this.createRadarChartWithData(containerId, data);
    },

    /**
     * Create radar chart with data once Chart.js is loaded
     * @param {string} containerId - ID of container element
     * @param {Object} data - Cluster characteristic data
     */
    createRadarChartWithData: function(containerId, data) {
      // Clear container
      const container = document.getElementById(containerId);
      container.innerHTML = "";

      // Create canvas
      const canvas = document.createElement("canvas");
      container.appendChild(canvas);

      // Normalize indicators for radar chart (0-100%)
      const normalizeValue = (value, indicator) => {
        switch (indicator) {
          case "x1":
            return Math.max(0, Math.min(100, (32 / value) * 100)); // Lower is better, max 32
          case "x2":
            // Assume 20 for SMA, 15 for SMK
            const ideal = 20; // We don't have jenjang info here, using SMA standard
            return Math.max(0, Math.min(100, (ideal / value) * 100)); // Lower is better
          case "x3":
            return Math.max(0, Math.min(100, (32 / value) * 100)); // Lower is better, max 32
          case "x4":
            // Ideal is between 3 and 27 for SMA, 3 and 48 for SMK
            // We'll use a bell curve with peak at 15 for SMA
            const mid = 15;
            if (value >= 3 && value <= 27) return 100; // In range
            if (value < 3) return (value / 3) * 100; // Below min
            return Math.max(0, 100 - ((value - 27) / 27) * 100); // Above max
          case "x5":
          case "x6":
          case "x7":
            return value * 100; // Already percentage
        }
        return 0;
      };

      // Get normalized values
      const values = [
        normalizeValue(data.x1_avg, "x1"),
        normalizeValue(data.x2_avg, "x2"),
        normalizeValue(data.x3_avg, "x3"),
        normalizeValue(data.x4_avg, "x4"),
        normalizeValue(data.x5_avg, "x5"),
        normalizeValue(data.x6_avg, "x6"),
        normalizeValue(data.x7_avg, "x7"),
      ];

      // Determine chart color based on quality level
      const qualityColor = this.getQualityColor(data.kualitas_pendidikan);
      const colorMap = {
        green: "rgb(34, 197, 94)",
        purple: "rgb(147, 51, 234)",
        yellow: "rgb(234, 179, 8)",
        orange: "rgb(249, 115, 22)",
        red: "rgb(239, 68, 68)",
      };
      const chartColor = colorMap[qualityColor] || "rgb(147, 51, 234)";

      // Create chart
      new Chart(canvas, {
        type: "radar",
        data: {
          labels: [
            "Siswa/Kelas",
            "Siswa/Guru",
            "Siswa/Rombel",
            "Rombel/Sekolah",
            "Perpustakaan",
            "Laboratorium",
            "Ruang Kelas",
          ],
          datasets: [
            {
              label: "Klaster " + data.cluster,
              data: values,
              backgroundColor: `${chartColor}33`,
              borderColor: chartColor,
              borderWidth: 2,
              pointBackgroundColor: chartColor,
              pointRadius: 3,
            },
          ],
        },
        options: {
          scales: {
            r: {
              angleLines: {
                display: true,
              },
              suggestedMin: 0,
              suggestedMax: 100,
              ticks: {
                display: false,
              },
            },
          },
          plugins: {
            legend: {
              display: false,
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  return `${context.dataset.label}: ${context.raw.toFixed(1)}%`;
                },
              },
            },
          },
          maintainAspectRatio: false,
        },
      });
    },

    /**
     * Get color for quality level
     * @param {string} quality - Quality level (tinggi, sedang, rendah, etc.)
     * @returns {string} - Color name
     */
    getQualityColor: function(quality) {
      switch (quality.toLowerCase()) {
        case "sangat tinggi":
          return "green";
        case "tinggi":
          return "green";
        case "sedang":
          return "yellow";
        case "rendah":
          return "orange";
        case "sangat rendah":
          return "red";
        default:
          return "purple";
      }
    },

    /**
     * Render characteristics in table view
     * @param {Array} characteristics - Array of cluster characteristics
     */
    renderTableView: function(characteristics) {
      const cardView = document.getElementById("karakteristik-card-view");
      const tableView = document.getElementById("karakteristik-table-view");
      const tableBody = document.getElementById("karakteristik-table-body");

      if (!tableView || !tableBody) return;

      // Show table view, hide card view
      tableView.classList.remove("hidden");
      if (cardView) cardView.classList.add("hidden");

      // Clear previous content
      tableBody.innerHTML = "";

      // Render each row
      characteristics.forEach((char) => {
        const rowHtml = this.generateCharacteristicRow(char);
        tableBody.insertAdjacentHTML("beforeend", rowHtml);
      });

      // Add click events for detail buttons
      document.querySelectorAll(".char-detail-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
          e.preventDefault();
          const clusterId = btn.getAttribute("data-cluster");

          // Find the characteristic data
          const char = characteristics.find((c) => c.cluster == clusterId);
          if (char) {
            this.showClusterDetail(char);
          }
        });
      });
    },

    /**
     * Generate HTML for a characteristic table row
     * @param {Object} char - Cluster characteristic data
     * @returns {string} - HTML string for table row
     */
    generateCharacteristicRow: function(char) {
      // Map quality level to badge color
      const qualityColor = this.getQualityColor(char.kualitas_pendidikan);
      const qualityBadgeClass = `bg-${qualityColor}-100 text-${qualityColor}-800`;

      // Format percentages consistently with 2 decimal places
      const x5Percent = (char.x5_avg * 100).toFixed(2);
      const x6Percent = (char.x6_avg * 100).toFixed(2);
      const x7Percent = (char.x7_avg * 100).toFixed(2);

      // Determine status for each indicator based on evaluations if available
      const getStatusClass = (indicator) => {
        if (char.evaluations && char.evaluations[indicator]) {
          return char.evaluations[indicator].status === "ideal"
            ? "text-green-600"
            : "text-red-600";
        }
        return "text-gray-500";
      };

      return `
        <tr>
          <td class="px-6 py-4 whitespace-nowrap">
            <div class="flex items-center">
              <div class="h-10 w-10 rounded-full bg-${qualityColor}-600 flex items-center justify-center text-white font-bold flex-shrink-0">
                ${char.cluster}
              </div>
              <div class="ml-4">
                <div class="text-sm font-medium text-gray-900">Klaster ${char.cluster}</div>
                <div class="text-sm text-gray-500">Medoid: ${char.medoid_name || "Tidak ada"}</div>
              </div>
            </div>
          </td>
          <td class="px-6 py-4 whitespace-nowrap">
            <span class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${qualityBadgeClass}">
              ${char.kualitas_pendidikan.charAt(0).toUpperCase() + char.kualitas_pendidikan.slice(1)}
            </span>
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            ${char.jumlah_anggota}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm ${getStatusClass("x1")}">
            ${char.x1_avg.toFixed(2)}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm ${getStatusClass("x2")}">
            ${char.x2_avg.toFixed(2)}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm ${getStatusClass("x3")}">
            ${char.x3_avg.toFixed(2)}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm ${getStatusClass("x4")}">
            ${char.x4_avg.toFixed(2)}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm ${getStatusClass("x5")}">
            ${x5Percent}%
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm ${getStatusClass("x6")}">
            ${x6Percent}%
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm ${getStatusClass("x7")}">
            ${x7Percent}%
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            ${char.standar_terpenuhi}/7
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
            <a href="#" class="text-indigo-600 hover:text-indigo-900 char-detail-btn" data-cluster="${char.cluster}">Detail</a>
          </td>
        </tr>
      `;
    },

    /**
     * Show cluster detail in a modal or panel
     * @param {Object} char - Cluster characteristic data
     */
    showClusterDetail: function(char) {
      // Implement modal or panel to show detailed cluster information
      // Could use a custom modal or the existing kecamatan-detail-modal
      alert(`Detail untuk Klaster ${char.cluster} akan ditampilkan di sini.`);
      console.log("Cluster detail:", char);
    },

    /**
     * Switch between card and table view
     * @param {string} view - 'card' or 'table'
     */
    switchView: function(view) {
      const cardViewBtn = document.getElementById("card-view-btn");
      const tableViewBtn = document.getElementById("table-view-btn");

      if (view === "card") {
        Klasterisasi.state.ui.characteristicsView = "card";

        // Update button styles
        if (cardViewBtn) {
          cardViewBtn.classList.remove("bg-gray-200", "text-gray-700");
          cardViewBtn.classList.add("bg-purple-600", "text-white");
        }
        if (tableViewBtn) {
          tableViewBtn.classList.remove("bg-purple-600", "text-white");
          tableViewBtn.classList.add("bg-gray-200", "text-gray-700");
        }
      } else {
        Klasterisasi.state.ui.characteristicsView = "table";

        // Update button styles
        if (cardViewBtn) {
          cardViewBtn.classList.remove("bg-purple-600", "text-white");
          cardViewBtn.classList.add("bg-gray-200", "text-gray-700");
        }
        if (tableViewBtn) {
          tableViewBtn.classList.remove("bg-gray-200", "text-gray-700");
          tableViewBtn.classList.add("bg-purple-600", "text-white");
        }
      }

      // Re-render with current data if available
      if (Klasterisasi.state.data.characteristics.length > 0) {
        this.renderCharacteristics();
      }
    },
  },

  /**
   * Module untuk tab Evaluasi Standar
   */
  evaluasiModule: {
    /**
     * Setup event listeners untuk tab Evaluasi Standar
     */
    setupEventListeners: function() {
      // Result selection change
      const resultSelect = document.getElementById("evaluasi-result-id");
      if (resultSelect) {
        resultSelect.addEventListener("change", () => {
          this.loadClustersForResult(resultSelect.value);
        });
      }

      // Filter form submit
      const filterForm = document.getElementById("evaluasi-filter-form");
      if (filterForm) {
        filterForm.addEventListener("submit", (e) => {
          e.preventDefault();
          this.loadEvaluationData();
        });
      }

      // Toggle between summary and detail views
      const summaryViewBtn = document.getElementById("summary-view-btn");
      const detailViewBtn = document.getElementById("detail-view-btn");

      if (summaryViewBtn) {
        summaryViewBtn.addEventListener("click", () => {
          this.switchView("summary");
        });
      }

      if (detailViewBtn) {
        detailViewBtn.addEventListener("click", () => {
          this.switchView("detail");
        });
      }

      // Toggle priority items accordion
      document.addEventListener("click", (e) => {
        if (e.target.closest(".priority-header")) {
          const header = e.target.closest(".priority-header");
          const content = header.nextElementSibling;
          const icon = header.querySelector("svg");

          if (content && icon) {
            content.classList.toggle("hidden");
            icon.classList.toggle("rotate-180");
          }
        }
      });
    },

    /**
     * Inisialisasi filter options untuk tab Evaluasi Standar
     */
    initFilterOptions: function() {
      // Fill result select box if empty
      const resultSelect = document.getElementById("evaluasi-result-id");

      if (resultSelect && resultSelect.options.length <= 1) {
        // Already loaded in the template by Jinja
        // Add event to trigger the first load if a result is selected
        if (resultSelect.value) {
          this.loadClustersForResult(resultSelect.value);
        }
      }
    },

    /**
     * Load cluster options for the selected result
     * @param {string} resultId - ID hasil klasterisasi yang dipilih
     */
    loadClustersForResult: function(resultId) {
      if (!resultId) return;

      const clusterSelect = document.getElementById("evaluasi-cluster");
      if (!clusterSelect) return;

      // Set the selected result in state
      Klasterisasi.state.data.selectedResult = resultId;

      // Clear current options except the first one
      while (clusterSelect.options.length > 1) {
        clusterSelect.remove(1);
      }

      // Add loading option
      const loadingOption = document.createElement("option");
      loadingOption.text = "Memuat klaster...";
      loadingOption.disabled = true;
      clusterSelect.add(loadingOption);
      clusterSelect.selectedIndex = clusterSelect.options.length - 1;

      // Fetch clusters for this result
      fetch(`${Klasterisasi.API.CLUSTERS}${resultId}`)
        .then((response) => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.json();
        })
        .then((data) => {
          // Remove loading option
          clusterSelect.remove(clusterSelect.options.length - 1);

          // Add cluster options
          if (data.clusters) {
            const clusters = Object.keys(data.clusters).sort((a, b) => parseInt(a) - parseInt(b));

            clusters.forEach((cluster) => {
              const option = document.createElement("option");
              option.value = cluster;
              option.text = `Klaster ${cluster} (${data.clusters[cluster]} kecamatan)`;
              clusterSelect.add(option);
            });
          }

          // Reset to "Semua Klaster"
          clusterSelect.selectedIndex = 0;
        })
        .catch((error) => {
          console.error("Error loading clusters:", error);
          // Remove loading option
          clusterSelect.remove(clusterSelect.options.length - 1);

          // Add error option
          const errorOption = document.createElement("option");
          errorOption.text = "Error memuat klaster";
          errorOption.disabled = true;
          clusterSelect.add(errorOption);
        });
    },

    /**
     * Load evaluasi standar data based on selected filters
     */
    loadEvaluationData: function() {
      const resultId = document.getElementById("evaluasi-result-id").value;
      const cluster = document.getElementById("evaluasi-cluster").value;
      const indikator = document.getElementById("evaluasi-indikator").value;

      if (!resultId) {
        Klasterisasi.utils.showErrorMessage("Silakan pilih hasil klasterisasi terlebih dahulu.");
        return;
      }

      // Show loading
      const loadingElement = document.getElementById("evaluasi-loading");
      const emptyState = document.getElementById("evaluasi-empty-state");
      const chartsContainer = document.getElementById("evaluasi-charts-container");

      if (loadingElement) loadingElement.classList.remove("hidden");
      if (emptyState) emptyState.classList.add("hidden");
      if (chartsContainer) chartsContainer.classList.add("hidden");

      Klasterisasi.state.loadingStates.evaluation = true;

      // Build the API URL with query parameters
      let apiUrl = `${Klasterisasi.API.EVALUATION}${resultId}`;
      const params = [];

      if (cluster) {
        params.push(`cluster=${cluster}`);
      }

      if (indikator) {
        params.push(`indikator=${indikator}`);
      }

      if (params.length > 0) {
        apiUrl += `?${params.join("&")}`;
      }

      // Fetch evaluation data
      fetch(apiUrl)
        .then((response) => {
          if (!response.ok) {
            throw new Error("Network response was not ok");
          }
          return response.json();
        })
        .then((data) => {
          // Store in state
          Klasterisasi.state.data.evaluation = data;

          // Render evaluation data
          this.renderEvaluationData(data);
        })
        .catch((error) => {
          console.error("Error loading evaluation data:", error);
          if (loadingElement) loadingElement.classList.add("hidden");

          Klasterisasi.utils.showErrorMessage("Gagal memuat data evaluasi standar. Silakan coba lagi.");
          Klasterisasi.state.loadingStates.evaluation = false;
        });
    },

    /**
     * Render evaluation data to UI
     * @param {Object} data - Evaluation data from API
     */
    renderEvaluationData: function(data) {
      const loadingElement = document.getElementById("evaluasi-loading");
      const emptyState = document.getElementById("evaluasi-empty-state");
      const chartsContainer = document.getElementById("evaluasi-charts-container");

      // Hide loading
      if (loadingElement) loadingElement.classList.add("hidden");

      // Check if data is empty or invalid
      if (!data || !data.evaluation_data || Object.keys(data.evaluation_data).length === 0) {
        if (emptyState) emptyState.classList.remove("hidden");
        if (chartsContainer) chartsContainer.classList.add("hidden");
        Klasterisasi.state.loadingStates.evaluation = false;
        return;
      }

      // Hide empty state, show container
      if (emptyState) emptyState.classList.add("hidden");
      if (chartsContainer) chartsContainer.classList.remove("hidden");

      // Render components
      this.renderStandarIndikator(data.standar_indikator);
      this.renderKPICards(data);
      this.renderCharts(data);
      this.renderIndicatorDetails(data);
      this.renderPriorityItems(data);

      Klasterisasi.state.loadingStates.evaluation = false;
    },

    /**
     * Render standar indikator information
     * @param {Object} standarData - Standard indicator data
     */
    renderStandarIndikator: function(standarData) {
      const container = document.getElementById("standar-indikator-list");
      if (!container || !standarData) return;

      // Clear previous content
      container.innerHTML = "";

      // Convert object to array for easier processing
      const indicators = Object.keys(standarData).map((key) => {
        return {
          code: key,
          ...standarData[key],
        };
      });

      // Split into two columns
      const midpoint = Math.ceil(indicators.length / 2);
      const leftCol = indicators.slice(0, midpoint);
      const rightCol = indicators.slice(midpoint);

      // Render left column
      const leftColHtml = this.renderStandarIndikatorColumn(leftCol);
      container.insertAdjacentHTML("beforeend", leftColHtml);

      // Render right column
      const rightColHtml = this.renderStandarIndikatorColumn(rightCol);
      container.insertAdjacentHTML("beforeend", rightColHtml);
    },

    /**
     * Render standar indikator column
     * @param {Array} indicators - List of indicators for column
     * @returns {string} - HTML for column
     */
    renderStandarIndikatorColumn: function(indicators) {
      return `
        <div>
          <ul class="space-y-2">
            ${indicators
              .map(
                (indicator) => `
              <li class="flex items-center">
                <span class="inline-flex items-center justify-center h-6 w-6 rounded-full bg-purple-100 text-purple-800 text-xs font-medium mr-2">${indicator.code.toUpperCase()}</span>
                <div>
                  <p class="font-medium text-gray-800">${indicator.desc}</p>
                  <p class="text-gray-600">${indicator.standard}</p>
                  <p class="text-xs text-gray-500 mt-0.5">${indicator.context}</p>
                </div>
              </li>
            `
              )
              .join("")}
          </ul>
        </div>
      `;
    },

    /**
     * Render KPI cards with overview metrics
     * @param {Object} data - Evaluation data
     */
    renderKPICards: function(data) {
      const container = document.getElementById("evaluasi-kpi-cards");
      if (!container || !data.evaluation_data) return;

      // Clear previous content
      container.innerHTML = "";

      // Count indicators meeting standards
      let standardsMet = 0;
      let totalStandards = 0;
      let bestIndicator = null;
      let bestPercentage = 0;
      let worstIndicator = null;
      let worstPercentage = 100;

      // Process each indicator
      Object.entries(data.evaluation_data).forEach(([indicator, info]) => {
        totalStandards++;
        const overall = info.overall;

        if (overall.status === "ideal") {
          standardsMet++;
        }

        // Check for best indicator
        if (overall.percentage > bestPercentage) {
          bestPercentage = overall.percentage;
          bestIndicator = {
            code: indicator,
            name: info.name,
            percentage: overall.percentage,
            value: overall.avg_value,
          };
        }

        // Check for worst indicator
        if (overall.percentage < worstPercentage) {
          worstPercentage = overall.percentage;
          worstIndicator = {
            code: indicator,
            name: info.name,
            percentage: overall.percentage,
            value: overall.avg_value,
          };
        }
      });

      // Calculate compliance percentage
      const compliancePercentage = (standardsMet / totalStandards) * 100;

      // Render KPI cards
      container.innerHTML = `
        <div class="bg-white rounded-xl shadow-md overflow-hidden p-4 border border-gray-200">
          <div class="flex items-start">
            <div class="bg-green-100 rounded-full p-3 mr-3">
              <svg class="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
              </svg>
            </div>
            <div>
              <h3 class="text-sm text-gray-500 font-medium">Indikator Memenuhi Standar</h3>
              <div class="flex items-baseline">
                <p class="text-3xl font-bold text-gray-800 mr-2">${standardsMet}</p>
                <p class="text-sm text-gray-600">dari ${totalStandards} indikator</p>
              </div>
              <p class="text-xs text-green-600 mt-1">${compliancePercentage.toFixed(1)}% kesesuaian dengan standar</p>
            </div>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2.5 mt-3">
            <div class="bg-green-600 h-2.5 rounded-full" style="width: ${compliancePercentage}%"></div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-md overflow-hidden p-4 border border-gray-200">
          <div class="flex items-start">
            <div class="bg-blue-100 rounded-full p-3 mr-3">
              <svg class="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"></path>
              </svg>
            </div>
            <div>
              <h3 class="text-sm text-gray-500 font-medium">Indikator Terbaik</h3>
              <div class="flex items-baseline">
                <p class="text-3xl font-bold text-gray-800 mr-2">${bestIndicator ? bestIndicator.code.toUpperCase() : "-"}</p>
                <p class="text-sm text-gray-600">${bestIndicator ? bestIndicator.name : ""}</p>
              </div>
              <p class="text-xs text-blue-600 mt-1">${bestIndicator ? bestIndicator.percentage.toFixed(1) + "% kesesuaian" : ""}</p>
            </div>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2.5 mt-3">
            <div class="bg-blue-600 h-2.5 rounded-full" style="width: ${bestIndicator ? bestIndicator.percentage : 0}%"></div>
          </div>
        </div>

        <div class="bg-white rounded-xl shadow-md overflow-hidden p-4 border border-gray-200">
          <div class="flex items-start">
            <div class="bg-red-100 rounded-full p-3 mr-3">
              <svg class="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z">
                </path>
              </svg>
            </div>
            <div>
              <h3 class="text-sm text-gray-500 font-medium">Prioritas Perbaikan</h3>
              <div class="flex items-baseline">
                <p class="text-3xl font-bold text-gray-800 mr-2">${worstIndicator ? worstIndicator.code.toUpperCase() : "-"}</p>
                <p class="text-sm text-gray-600">${worstIndicator ? worstIndicator.name : ""}</p>
              </div>
              <p class="text-xs text-red-600 mt-1">${worstIndicator ? worstIndicator.percentage.toFixed(1) + "% kesesuaian" : ""}</p>
            </div>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2.5 mt-3">
            <div class="bg-red-600 h-2.5 rounded-full" style="width: ${worstIndicator ? worstIndicator.percentage : 0}%"></div>
          </div>
        </div>
      `;
    },

    /**
     * Render charts for evaluation data
     * @param {Object} data - Evaluation data
     */
    renderCharts: function(data) {
      // Compliance bar chart
      this.renderComplianceChart(data);

      // Overall pie chart
      this.renderPieChart(data);
    },

    /**
     * Render compliance bar chart
     * @param {Object} data - Evaluation data
     */
    renderComplianceChart: function(data) {
      const container = document.getElementById("evaluasi-compliance-chart");
      if (!container || !data.evaluation_data) return;

      // Clear container
      container.innerHTML = "";

      // Create canvas
      const canvas = document.createElement("canvas");
      container.appendChild(canvas);

      // Try to load Chart.js dynamically if not available
      if (typeof Chart === "undefined") {
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/chart.js";
        script.onload = () => this.createComplianceChart(canvas, data);
        document.head.appendChild(script);
        return;
      }

      this.createComplianceChart(canvas, data);
    },

    /**
     * Create compliance bar chart once Chart.js is loaded
     * @param {HTMLElement} canvas - Canvas element
     * @param {Object} data - Evaluation data
     */
    createComplianceChart: function(canvas, data) {
      // Prepare data for chart
      const labels = [];
      const percentages = [];
      const backgroundColors = [];

      Object.entries(data.evaluation_data).forEach(([indicator, info]) => {
        labels.push(indicator.toUpperCase());
        percentages.push(info.overall.percentage);

        // Color based on status
        if (info.overall.status === "ideal") {
          backgroundColors.push("rgba(34, 197, 94, 0.7)"); // Green
        } else {
          backgroundColors.push("rgba(239, 68, 68, 0.7)"); // Red
        }
      });

      // Create chart
      new Chart(canvas, {
        type: "bar",
        data: {
          labels: labels,
          datasets: [
            {
              label: "Kesesuaian dengan Standar (%)",
              data: percentages,
              backgroundColor: backgroundColors,
              borderColor: backgroundColors.map((color) => color.replace("0.7", "1")),
              borderWidth: 1,
            },
          ],
        },
        options: {
          indexAxis: "y",
          scales: {
            x: {
              beginAtZero: true,
              max: 100,
              title: {
                display: true,
                text: "Persentase Kesesuaian (%)",
              },
            },
            y: {
              title: {
                display: true,
                text: "Indikator",
              },
            },
          },
          plugins: {
            tooltip: {
              callbacks: {
                label: function(context) {
                  const indicator = context.label.toLowerCase();
                  const info = data.evaluation_data[indicator];
                  const statusText = info.overall.status === "ideal" ? "Memenuhi Standar" : "Tidak Memenuhi Standar";
                  return [`Kesesuaian: ${context.raw.toFixed(1)}%`, `Status: ${statusText}`];
                },
              },
            },
          },
        },
      });
    },

    /**
     * Render pie chart for overall compliance
     * @param {Object} data - Evaluation data
     */
    renderPieChart: function(data) {
      const container = document.getElementById("evaluasi-pie-chart");
      if (!container || !data.evaluation_data) return;

      // Clear container
      container.innerHTML = "";

      // Create canvas
      const canvas = document.createElement("canvas");
      container.appendChild(canvas);

      // Try to load Chart.js dynamically if not available
      if (typeof Chart === "undefined") {
        const script = document.createElement("script");
        script.src = "https://cdn.jsdelivr.net/npm/chart.js";
        script.onload = () => this.createPieChart(canvas, data);
        document.head.appendChild(script);
        return;
      }

      this.createPieChart(canvas, data);
    },

    /**
     * Create pie chart once Chart.js is loaded
     * @param {HTMLElement} canvas - Canvas element
     * @param {Object} data - Evaluation data
     */
    createPieChart: function(canvas, data) {
      // Count compliant and non-compliant indicators
      let compliant = 0;
      let nonCompliant = 0;

      Object.values(data.evaluation_data).forEach((info) => {
        if (info.overall.status === "ideal") {
          compliant++;
        } else {
          nonCompliant++;
        }
      });

      // Create chart
      new Chart(canvas, {
        type: "pie",
        data: {
          labels: ["Memenuhi Standar", "Tidak Memenuhi Standar"],
          datasets: [
            {
              data: [compliant, nonCompliant],
              backgroundColor: ["rgba(34, 197, 94, 0.7)", "rgba(239, 68, 68, 0.7)"],
              borderColor: ["rgba(34, 197, 94, 1)", "rgba(239, 68, 68, 1)"],
              borderWidth: 1,
            },
          ],
        },
        options: {
          plugins: {
            tooltip: {
              callbacks: {
                label: function(context) {
                  const label = context.label || "";
                  const value = context.raw;
                  const total = compliant + nonCompliant;
                  const percentage = ((value / total) * 100).toFixed(1);
                  return `${label}: ${value} (${percentage}%)`;
                },
              },
            },
          },
        },
      });
    },

    /**
     * Render indicator details in summary and detail views
     * @param {Object} data - Evaluation data
     */
    renderIndicatorDetails: function(data) {
      this.renderSummaryView(data);
      this.renderDetailView(data);

      // Show the appropriate view based on current state
      this.switchView(Klasterisasi.state.ui.evaluationView);
    },

    /**
     * Render summary view of indicators
     * @param {Object} data - Evaluation data
     */
    renderSummaryView: function(data) {
      const container = document.getElementById("summary-view");
      if (!container || !data.evaluation_data) return;

      // Clear previous content
      container.innerHTML = "";

      // Sort indicators by compliance percentage (ascending)
      const sortedIndicators = Object.entries(data.evaluation_data)
        .map(([indicator, info]) => ({
          code: indicator,
          name: info.name,
          ...info.overall,
        }))
        .sort((a, b) => a.percentage - b.percentage);

      // Render each indicator card
      sortedIndicators.forEach((indicator) => {
        const cardHtml = this.generateIndicatorCard(indicator, data.jenjang);
        container.insertAdjacentHTML("beforeend", cardHtml);
      });
    },

    /**
     * Generate HTML for an indicator summary card
     * @param {Object} indicator - Indicator data
     * @param {string} jenjang - Education level (SMA/SMK)
     * @returns {string} - HTML string for card
     */
    generateIndicatorCard: function(indicator, jenjang) {
      // Determine status styling
      const isIdeal = indicator.status === "ideal";
      const statusClass = isIdeal ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800";
      const statusText = isIdeal ? "Memenuhi Standar" : "Tidak Memenuhi Standar";

      // Format value based on indicator
      let formattedValue = indicator.avg_value.toFixed(1);
      if (["x5", "x6", "x7"].includes(indicator.code)) {
        formattedValue = (indicator.avg_value * 100).toFixed(1) + "%";
      }

      // Get standard for comparison
      let standardText = "";
      switch (indicator.code) {
        case "x1":
          standardText = "≤ 32";
          break;
        case "x2":
          standardText = jenjang === "SMA" ? "≤ 20" : "≤ 15";
          break;
        case "x3":
          standardText = "≤ 32";
          break;
        case "x4":
          standardText = jenjang === "SMA" ? "3-27" : "3-48";
          break;
        case "x5":
        case "x6":
        case "x7":
          standardText = "100%";
          break;
      }

      return `
        <div class="p-4 border border-gray-200 rounded-lg">
          <div class="flex justify-between items-center mb-2">
            <div class="flex items-center">
              <span class="inline-flex items-center justify-center h-7 w-7 rounded-full bg-purple-100 text-purple-800 text-sm font-medium mr-2">${indicator.code.toUpperCase()}</span>
              <h4 class="font-medium text-gray-800">${indicator.name}</h4>
            </div>
            <span class="px-2 py-1 text-xs rounded-full ${statusClass} font-medium">${statusText}</span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-2">
            <div>
              <p class="text-xs text-gray-500">Nilai Rata-rata</p>
              <p class="text-lg font-bold text-gray-800">${formattedValue}</p>
            </div>
            <div>
              <p class="text-xs text-gray-500">Standar Ideal</p>
              <p class="text-lg font-bold text-blue-700">${standardText}</p>
            </div>
            <div>
              <p class="text-xs text-gray-500">Kesesuaian</p>
              <p class="text-lg font-bold ${isIdeal ? "text-green-600" : "text-red-600"}">${indicator.percentage.toFixed(1)}%</p>
            </div>
            <div>
              <p class="text-xs text-gray-500">Status</p>
              <p class="text-lg font-bold text-gray-800">${statusText}</p>
            </div>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2 mb-3">
            <div class="${isIdeal ? "bg-green-600" : "bg-red-600"} h-2 rounded-full" style="width: ${
        indicator.percentage
      }%"></div>
          </div>
          <p class="text-sm text-gray-600">
            <span class="font-medium">Deskripsi:</span>
            ${indicator.description || "Tidak ada deskripsi."}
          </p>
          ${
            !isIdeal
              ? `
            <div class="mt-2 bg-yellow-50 border-l-4 border-yellow-400 p-3">
              <p class="text-sm text-yellow-800">
                <span class="font-medium">Rekomendasi:</span>
                Perlu perbaikan untuk meningkatkan nilai indikator ${indicator.code.toUpperCase()} (${indicator.name}).
              </p>
            </div>
          `
              : ""
          }
        </div>
      `;
    },

    /**
     * Render detail view of indicators by cluster
     * @param {Object} data - Evaluation data
     */
    renderDetailView: function(data) {
      const tableBody = document.getElementById("evaluasi-table-body");
      if (!tableBody || !data.evaluation_data) return;

      // Clear previous content
      tableBody.innerHTML = "";

      // Flatten and prepare data for table
      const rows = [];

      Object.entries(data.evaluation_data).forEach(([indicator, info]) => {
        const indicatorName = info.name;

        // Add rows for each cluster
        Object.entries(info.clusters).forEach(([cluster, clusterData]) => {
          rows.push({
            indicator,
            indicatorName,
            cluster,
            avg_value: clusterData.avg_value,
            percentage: clusterData.percentage,
            status: clusterData.status,
            description: clusterData.description,
          });
        });
      });

      // Sort by indicator, then by cluster
      rows.sort((a, b) => {
        if (a.indicator !== b.indicator) {
          return a.indicator.localeCompare(b.indicator);
        }
        return parseInt(a.cluster) - parseInt(b.cluster);
      });

      // Render rows
      rows.forEach((row) => {
        const rowHtml = this.generateDetailRow(row);
        tableBody.insertAdjacentHTML("beforeend", rowHtml);
      });
    },

    /**
     * Generate HTML for a detail table row
     * @param {Object} row - Row data
     * @returns {string} - HTML string for table row
     */
    generateDetailRow: function(row) {
      // Format value if percentage
      let formattedValue = row.avg_value.toFixed(1);
      if (["x5", "x6", "x7"].includes(row.indicator)) {
        formattedValue = (row.avg_value * 100).toFixed(1) + "%";
      }

      // Status badge
      const statusClass = row.status === "ideal" ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800";
      const statusText = row.status === "ideal" ? "Ideal" : "Kurang Ideal";

      return `
        <tr>
          <td class="px-6 py-4 whitespace-nowrap">
            <div class="flex items-center">
              <span class="inline-flex items-center justify-center h-6 w-6 rounded-full bg-purple-100 text-purple-800 text-xs font-medium mr-2">${row.indicator.toUpperCase()}</span>
              <span>${row.indicatorName}</span>
            </div>
          </td>
          <td class="px-6 py-4 whitespace-nowrap">
            <div class="text-sm text-gray-900 font-medium">Klaster ${row.cluster}</div>
          </td>
          <td class="px-6 py-4 whitespace-nowrap">
            <div class="text-sm text-gray-900">${formattedValue}</div>
          </td>
          <td class="px-6 py-4 whitespace-nowrap">
            <div class="text-sm text-gray-900">${row.percentage.toFixed(1)}%</div>
          </td>
          <td class="px-6 py-4 whitespace-nowrap">
            <span class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${statusClass}">
              ${statusText}
            </span>
          </td>
          <td class="px-6 py-4 whitespace-normal text-sm text-gray-500 max-w-md">
            ${row.description}
          </td>
        </tr>
      `;
    },

    /**
     * Switch between summary and detail views
     * @param {string} view - 'summary' or 'detail'
     */
    switchView: function(view) {
      const summaryViewBtn = document.getElementById("summary-view-btn");
      const detailViewBtn = document.getElementById("detail-view-btn");
      const summaryView = document.getElementById("summary-view");
      const detailView = document.getElementById("detail-view");

      if (view === "summary") {
        Klasterisasi.state.ui.evaluationView = "summary";

        // Update button styles
        if (summaryViewBtn) {
          summaryViewBtn.classList.remove("bg-gray-100", "text-gray-700");
          summaryViewBtn.classList.add("bg-purple-600", "text-white");
        }
        if (detailViewBtn) {
          detailViewBtn.classList.remove("bg-purple-600", "text-white");
          detailViewBtn.classList.add("bg-gray-100", "text-gray-700");
        }

        // Show/hide views
        if (summaryView) summaryView.classList.remove("hidden");
        if (detailView) detailView.classList.add("hidden");
      } else {
        Klasterisasi.state.ui.evaluationView = "detail";

        // Update button styles
        if (summaryViewBtn) {
          summaryViewBtn.classList.remove("bg-purple-600", "text-white");
          summaryViewBtn.classList.add("bg-gray-100", "text-gray-700");
        }
        if (detailViewBtn) {
          detailViewBtn.classList.remove("bg-gray-100", "text-gray-700");
          detailViewBtn.classList.add("bg-purple-600", "text-white");
        }

        // Show/hide views
        if (summaryView) summaryView.classList.add("hidden");
        if (detailView) detailView.classList.remove("hidden");
      }
    },

    /**
     * Render priority recommendation items
     * @param {Object} data - Evaluation data
     */
    renderPriorityItems: function(data) {
      const container = document.getElementById("prioritas-container");
      if (!container || !data.rekomendasi) return;

      // Clear previous content
      container.innerHTML = "";

      // Get non-ideal indicators sorted by percentage
      const nonIdealIndicators = [];

      Object.entries(data.evaluation_data).forEach(([indicator, info]) => {
        if (info.overall.status !== "ideal") {
          nonIdealIndicators.push({
            code: indicator,
            name: info.name,
            percentage: info.overall.percentage,
            avg_value: info.overall.avg_value,
            context: info.context,
          });
        }
      });

      // Sort by percentage (ascending)
      nonIdealIndicators.sort((a, b) => a.percentage - b.percentage);

      // Filter to top 3
      const priorityIndicators = nonIdealIndicators.slice(0, 3);

      // If no priorities, show message
      if (priorityIndicators.length === 0) {
        container.innerHTML = `
          <div class="bg-green-50 border-l-4 border-green-400 p-4">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <p class="text-sm text-green-700">
                  Semua indikator telah memenuhi standar ideal. Tidak ada prioritas perbaikan yang diperlukan.
                </p>
              </div>
            </div>
          </div>
        `;
        return;
      }

      // Render priority items
      priorityIndicators.forEach((indicator, index) => {
        // Konsistensi: selalu gunakan warna merah untuk prioritas
        const urgencyColor = "red";

        // Format nilai untuk ditampilkan
        const formattedValue = ["x5", "x6", "x7"].includes(indicator.code)
          ? (indicator.avg_value * 100).toFixed(1) + "%"
          : indicator.avg_value.toFixed(1);

        const standardText = this.getStandardText(indicator.code, data.jenjang);
        const rekomendasi = this.findRekomendasi(data.rekomendasi, indicator.code);

        const html = `
            <div class="border border-gray-200 rounded-lg overflow-hidden mb-3">
                <div class="bg-${urgencyColor}-50 px-4 py-3 border-b border-${urgencyColor}-100 flex justify-between items-center cursor-pointer priority-header">
                    <div class="flex items-center">
                        <div class="bg-${urgencyColor}-100 rounded-full p-1.5 mr-3">
                            <span class="inline-block w-5 h-5 bg-${urgencyColor}-600 rounded-full text-white text-xs font-bold flex items-center justify-center">${index + 1}</span>
                        </div>
                        <div>
                            <h4 class="font-medium text-gray-900">${indicator.name} (${indicator.code.toUpperCase()})</h4>
                            <p class="text-sm text-${urgencyColor}-700">${formattedValue} (standar ${standardText}) - Kesesuaian ${indicator.percentage.toFixed(1)}%</p>
                        </div>
                    </div>
                    <svg class="w-5 h-5 text-gray-500 transform transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                    </svg>
                </div>
                <div class="p-4 hidden">
                    <div class="mb-3">
                        <h5 class="text-sm font-semibold text-gray-700 mb-1">Kondisi Saat Ini:</h5>
                        <p class="text-sm text-gray-600">Nilai rata-rata untuk indikator ${indicator.code.toUpperCase()} (${indicator.name}) adalah ${formattedValue}, sedangkan standar ideal adalah ${standardText}.</p>
                    </div>
                    
                    ${rekomendasi ? `
                    <div class="mb-3">
                        <h5 class="text-sm font-semibold text-gray-700 mb-1">Rekomendasi Tindakan:</h5>
                        <p class="text-sm text-gray-600">${rekomendasi}</p>
                    </div>
                    ` : ''}
                    
                    <div>
                        <h5 class="text-sm font-semibold text-gray-700 mb-1">Indikator Terkait:</h5>
                        <p class="text-sm text-gray-600">Peningkatan pada indikator ini dapat berdampak positif pada kualitas pendidikan secara keseluruhan.</p>
                    </div>
                </div>
            </div>
        `;

        container.insertAdjacentHTML("beforeend", html);
      });

      // Add click events for priority headers
      document.querySelectorAll(".priority-header").forEach((header) => {
        header.addEventListener("click", function() {
          const content = this.nextElementSibling;
          const arrow = this.querySelector("svg");
          content.classList.toggle("hidden");
          arrow.classList.toggle("rotate-180");
        });
      });
    },

    /**
     * Get urgency level based on percentage
     * @param {number} percentage - Compliance percentage
     * @returns {string} - Urgency level
     */
    getUrgencyLevel: function(percentage) {
      if (percentage < 50) return "tinggi";
      if (percentage < 75) return "sedang";
      return "rendah";
    },

    /**
     * Get standard text for an indicator
     * @param {string} indicator - Indicator code
     * @param {string} jenjang - Education level
     * @returns {string} - Standard text
     */
    getStandardText: function(indicator, jenjang) {
      switch (indicator) {
        case "x1":
          return "≤ 32";
        case "x2":
          return jenjang === "SMA" ? "≤ 20" : "≤ 15";
        case "x3":
          return "≤ 32";
        case "x4":
          return jenjang === "SMA" ? "3-27" : "3-48";
        case "x5":
        case "x6":
        case "x7":
          return "100%";
        default:
          return "";
      }
    },

    /**
     * Find recommendation for an indicator
     * @param {Array} rekomendasi - Recommendations data
     * @param {string} indicator - Indicator code
     * @returns {string} - Recommendation text
     */
    findRekomendasi: function(rekomendasi, indicator) {
      if (!rekomendasi || rekomendasi.length === 0) return null;

      // Find recommendations for this indicator
      const matchingRecs = rekomendasi.filter((rec) => {
        return (
          rec.prioritas_1 === indicator ||
          rec.prioritas_2 === indicator ||
          rec.prioritas_3 === indicator
        );
      });

      if (matchingRecs.length === 0) return null;

      // Get the first matching recommendation text
      for (const rec of matchingRecs) {
        if (rec.prioritas_1 === indicator && rec.keterangan_prioritas_1) {
          return rec.keterangan_prioritas_1;
        } else if (rec.prioritas_2 === indicator && rec.keterangan_prioritas_2) {
          return rec.keterangan_prioritas_2;
        } else if (rec.prioritas_3 === indicator && rec.keterangan_prioritas_3) {
          return rec.keterangan_prioritas_3;
        }
      }

      return null;
    },
  },
};

/**
 * Utility functions
 */
Klasterisasi.utils = {
  /**
   * Show success message
   * @param {string} message - Success message
   */
  showSuccessMessage: function(message) {
    this.showMessage(message, "success");
  },

  /**
   * Show error message
   * @param {string} message - Error message
   */
  showErrorMessage: function(message) {
    this.showMessage(message, "danger");
  },

  /**
   * Show info message
   * @param {string} message - Info message
   */
  showInfoMessage: function(message) {
    this.showMessage(message, "info");
  },

  /**
   * Show message with specified category
   * @param {string} message - Message text
   * @param {string} category - Message category (success, danger, info)
   */
  showMessage: function(message, category) {
    // Remove existing messages
    document.querySelectorAll(".temp-message").forEach((el) => el.remove());

    // Create message
    const messageDiv = document.createElement("div");
    messageDiv.className = `alert alert-${category} bg-${
      category === "success" || category === "info" ? "green" : "red"
    }-100 border-${
      category === "success" || category === "info" ? "green" : "red"
    }-400 text-${
      category === "success" || category === "info" ? "green" : "red"
    }-700 px-4 py-3 rounded relative mb-4 temp-message`;

    // Add message content
    messageDiv.innerHTML = `
      <span class="block sm:inline">${message}</span>
      <button class="absolute top-0 bottom-0 right-0 px-4 py-3 alert-close">
        <svg class="fill-current h-6 w-6 text-${
          category === "success" || category === "info" ? "green" : "red"
        }-500" role="button" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
          <title>Close</title>
          <path d="M14.348 14.849a1.2 1.2 0 0 1-1.697 0L10 11.819l-2.651 3.029a1.2 1.2 0 1 1-1.697-1.697l2.758-3.15-2.759-3.152a1.2 1.2 0 1 1 1.697-1.697L10 8.183l2.651-3.031a1.2 1.2 0 1 1 1.697 1.697l-2.758 3.152 2.758 3.15a1.2 1.2 0 0 1 0 1.698z" />
        </svg>
      </button>
    `;

    // Add click event to close button
    const closeButton = messageDiv.querySelector(".alert-close");
    closeButton.addEventListener("click", () => {
      messageDiv.remove();
    });

    // Insert after header if present, otherwise at start of main content
    const mainContent = document.getElementById("main-content");
    const firstElement = mainContent?.firstChild;

    if (mainContent) {
      mainContent.insertBefore(messageDiv, firstElement);
    } else {
      // Fallback - append to body
      document.body.appendChild(messageDiv);
    }

    // Auto-remove after delay
    setTimeout(() => {
      if (document.body.contains(messageDiv)) {
        // Fade out effect
        messageDiv.style.opacity = "1";
        messageDiv.style.transition = "opacity 0.5s";
        messageDiv.style.opacity = "0";

        setTimeout(() => {
          if (document.body.contains(messageDiv)) {
            messageDiv.remove();
          }
        }, 500);
      }
    }, 5000);
  },

  /**
   * Format date for display
   * @param {string|Date} dateString - Date string or object
   * @param {boolean} includeTime - Whether to include time in the formatted output
   * @returns {string} - Formatted date string
   */
  formatDate: function(dateString, includeTime = true) {
    if (!dateString) return "-";

    const date = new Date(dateString);
    if (isNaN(date)) return dateString; // Return as is if invalid date

    const options = {
      year: "numeric",
      month: "long",
      day: "numeric",
    };

    if (includeTime) {
      options.hour = "2-digit";
      options.minute = "2-digit";
    }

    return date.toLocaleDateString("id-ID", options);
  },

  /**
   * Format number with thousand separators
   * @param {number} number - Number to format
   * @param {number} decimals - Number of decimal places
   * @returns {string} - Formatted number string
   */
  formatNumber: function(number, decimals = 0) {
    if (number === null || number === undefined) return "-";

    return number.toLocaleString("id-ID", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  },

  /**
   * Format percentage value
   * @param {number} value - Value to format (0-1 or 0-100)
   * @param {boolean} convertFrom01 - Whether value is in 0-1 range and needs conversion to percentage
   * @returns {string} - Formatted percentage string
   */
  formatPercentage: function(value, convertFrom01 = false) {
    if (value === null || value === undefined) return "-";

    // Convert from 0-1 to 0-100 if needed
    const percentage = convertFrom01 ? value * 100 : value;

    return percentage.toLocaleString("id-ID", {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    }) + "%";
  },

  /**
   * Get color for quality level
   * @param {string} quality - Quality level (tinggi, sedang, rendah, etc.)
   * @returns {string} - Color name for Tailwind CSS
   */
  getQualityColor: function(quality) {
    if (!quality) return "purple";

    switch (quality.toLowerCase()) {
      case "sangat tinggi":
        return "green";
      case "tinggi":
        return "green";
      case "sedang":
        return "yellow";
      case "rendah":
        return "orange";
      case "sangat rendah":
        return "red";
      default:
        return "purple";
    }
  },
};

// Initialize application
Klasterisasi.init();