/**
 * Bengal Data Table Initialization
 *
 * Auto-initializes Tabulator tables for data-table directives.
 * Provides Bengal-specific theming and configuration.
 */

(function() {
  'use strict';

  // Ensure utils are available
  if (!window.BengalUtils) {
    console.error('BengalUtils not loaded - data-table.js requires utils.js');
    return;
  }

  const { log, debounce, ready } = window.BengalUtils;

  /**
   * Initialize all data tables on the page
   */
  function initDataTables() {
    // Check if Tabulator is available
    if (typeof Tabulator === 'undefined') {
      console.error('Tabulator library not loaded - data tables will not work');
      return;
    }

    // Find all data table wrappers
    const tableWrappers = document.querySelectorAll('.bengal-data-table-wrapper');

    if (tableWrappers.length === 0) {
      return; // No tables on this page
    }

    log(`Initializing ${tableWrappers.length} data table(s)`);

    tableWrappers.forEach(wrapper => {
      initSingleTable(wrapper);
    });
  }

  /**
   * Initialize a single data table
   * @param {HTMLElement} wrapper - Table wrapper element
   */
  function initSingleTable(wrapper) {
    const tableId = wrapper.getAttribute('data-table-id');
    const tableElement = wrapper.querySelector(`#${tableId}`);
    const searchInput = wrapper.querySelector(`#${tableId}-search`);
    const configScript = wrapper.querySelector(`script[data-table-config="${tableId}"]`);

    if (!tableElement || !configScript) {
      console.error(`Data table ${tableId} missing required elements`);
      return;
    }

    // Parse configuration
    let config;
    try {
      config = JSON.parse(configScript.textContent);
    } catch (e) {
      console.error(`Failed to parse config for table ${tableId}:`, e);
      return;
    }

    // Apply Bengal theme customizations
    config = applyBengalTheme(config);

    // Initialize Tabulator
    let table;
    try {
      table = new Tabulator(tableElement, config);
    } catch (e) {
      console.error(`Failed to initialize table ${tableId}:`, e);
      return;
    }

    // Connect search input if present
    if (searchInput && config.data) {
      searchInput.addEventListener('input', debounce(function(e) {
        table.setFilter(matchAny, e.target.value);
      }, 300));

      // Clear search on Escape key
      searchInput.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
          searchInput.value = '';
          table.clearFilter();
        }
      });
    }

    // Store table instance on wrapper for external access
    wrapper._tabulatorInstance = table;

    log(`Initialized table ${tableId}`);
  }

  /**
   * Apply Bengal-specific theme and configuration
   * @param {Object} config - Tabulator config
   * @returns {Object} Modified config
   */
  function applyBengalTheme(config) {
    // Default column settings
    if (config.columns) {
      config.columns = config.columns.map(col => ({
        ...col,
        resizable: true,
        headerSort: config.sort !== false,
        headerTooltip: true,
      }));
    }

    // Pagination settings
    if (config.pagination) {
      config.paginationMode = 'local';
      config.paginationSizeSelector = [10, 25, 50, 100, 200];
      config.paginationCounter = 'rows';
    }

    // Accessibility
    config.tabEndNewRow = false;
    config.keybindings = {
      navPrev: "shift + 9",
      navNext: 9,
      navUp: 38,
      navDown: 40,
    };

    // Mobile responsiveness
    config.responsiveLayout = 'collapse';
    config.responsiveLayoutCollapseStartOpen = false;

    // Performance
    config.virtualDom = true;
    config.virtualDomBuffer = 300;

    return config;
  }

  /**
   * Custom filter function for search across all columns
   * @param {Object} data - Row data
   * @param {Object} filterParams - Filter parameters
   * @returns {boolean} Whether row matches
   */
  function matchAny(data, filterParams) {
    // Handle empty, null, or undefined
    if (!filterParams || typeof filterParams !== 'string' || filterParams.trim() === '') {
      return true;
    }

    const searchTerm = filterParams.toLowerCase();

    // Search across all values in the row
    return Object.values(data).some(value => {
      if (value === null || value === undefined) {
        return false;
      }
      return String(value).toLowerCase().includes(searchTerm);
    });
  }


  /**
   * Export table data (future feature)
   * @param {string} tableId - Table ID
   * @param {string} format - Export format (csv, json, xlsx)
   */
  function exportTable(tableId, format = 'csv') {
    const wrapper = document.querySelector(`[data-table-id="${tableId}"]`);
    if (!wrapper || !wrapper._tabulatorInstance) {
      console.error(`Table ${tableId} not found`);
      return;
    }

    const table = wrapper._tabulatorInstance;

    switch(format) {
      case 'csv':
        table.download('csv', `${tableId}.csv`);
        break;
      case 'json':
        table.download('json', `${tableId}.json`);
        break;
      default:
        console.warn(`Export format ${format} not supported`);
    }
  }

  // Auto-initialize on DOM ready
  ready(initDataTables);

  // Expose API for programmatic access
  window.BengalDataTable = {
    init: initDataTables,
    export: exportTable,
  };

})();
