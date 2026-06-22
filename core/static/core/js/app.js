document.addEventListener('DOMContentLoaded', function () {

  // ===== 1. Sidebar toggle with persistence =====
  var sidebar = document.getElementById('sidebar');
  var mainContent = document.getElementById('main-content');
  var sidebarOverlay = document.getElementById('sidebar-overlay');
  var toggleBtn = document.getElementById('sidebar-toggle');
  var SIDEBAR_KEY = 'sidebar_state';

  function isDesktop() { return window.innerWidth >= 992; }
  function isTablet() { return window.innerWidth >= 768 && window.innerWidth < 992; }
  function isMobile() { return window.innerWidth < 768; }

  function expandSidebar() {
    sidebar.classList.add('sidebar--expanded');
    if (isDesktop()) {
      mainContent.classList.add('content--shifted');
    }
    if (isTablet() || isMobile()) {
      sidebarOverlay.classList.add('sidebar-overlay--visible');
    }
    localStorage.setItem(SIDEBAR_KEY, 'expanded');
  }

  function collapseSidebar() {
    sidebar.classList.remove('sidebar--expanded');
    mainContent.classList.remove('content--shifted');
    sidebarOverlay.classList.remove('sidebar-overlay--visible');
    if (isMobile()) {
      sidebar.style.transform = 'translateX(-100%)';
    }
    localStorage.setItem(SIDEBAR_KEY, 'mini');
  }

  function toggleSidebar() {
    if (sidebar.classList.contains('sidebar--expanded')) {
      collapseSidebar();
    } else {
      expandSidebar();
    }
  }

  // Restore state on load
  var saved = localStorage.getItem(SIDEBAR_KEY);
  if (saved === 'expanded' && !isMobile()) {
    expandSidebar();
  } else if (isMobile()) {
    sidebar.style.transform = 'translateX(-100%)';
  }

  if (toggleBtn) {
    toggleBtn.addEventListener('click', toggleSidebar);
  }

  // Overlay click closes sidebar
  if (sidebarOverlay) {
    sidebarOverlay.addEventListener('click', collapseSidebar);
  }

  // Handle resize
  var resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      if (isDesktop()) {
        if (localStorage.getItem(SIDEBAR_KEY) === 'expanded') {
          expandSidebar();
        } else {
          collapseSidebar();
        }
      } else if (isTablet()) {
        collapseSidebar();
      } else {
        sidebar.style.transform = 'translateX(-100%)';
        if (sidebar.classList.contains('sidebar--expanded')) {
          sidebarOverlay.classList.add('sidebar-overlay--visible');
        }
      }
    }, 150);
  });

  // ===== 2. Auto-dismiss messages after 4 seconds =====
  var messages = document.querySelectorAll('.alert-dismissible-custom');
  messages.forEach(function (msg) {
    setTimeout(function () {
      msg.style.transition = 'opacity 0.3s ease';
      msg.style.opacity = '0';
      setTimeout(function () {
        msg.remove();
      }, 300);
    }, 4000);
  });

  // ===== 3. Confirm delete with modal =====
  var deleteForms = document.querySelectorAll('[data-confirm-delete]');
  deleteForms.forEach(function (form) {
    form.addEventListener('submit', function (e) {
      if (!confirm(form.getAttribute('data-confirm-delete') || 'Tem certeza que deseja excluir este item?')) {
        e.preventDefault();
      }
    });
  });

  // ===== 4. Manutencao form: show/hide data_conclusao based on status =====
  var statusSelect = document.getElementById('id_status');
  var dataConclusaoField = document.getElementById('id_data_conclusao');
  if (statusSelect && dataConclusaoField) {
    function toggleDataConclusao() {
      var fieldGroup = dataConclusaoField.closest('.form-group-custom') || dataConclusaoField.closest('.mb-3');
      if (fieldGroup) {
        fieldGroup.style.display = statusSelect.value === 'CONCLUIDA' ? '' : 'none';
      }
    }
    toggleDataConclusao();
    statusSelect.addEventListener('change', toggleDataConclusao);
  }

  // ===== 5. Movimentacao form: show equipamento field only for SAIDA =====
  var movItemSelect = document.getElementById('id_item');
  var movTipoSelect = document.getElementById('id_tipo');
  var movEquipamentoField = document.getElementById('id_equipamento');
  // Only run on Movimentacao page (has id_item), not on Manutencao (same id_tipo/id_equipamento)
  if (movItemSelect && movTipoSelect && movEquipamentoField) {
    function toggleEquipamentoField() {
      var fieldGroup = movEquipamentoField.closest('.form-group-custom') || movEquipamentoField.closest('.mb-3');
      if (fieldGroup) {
        fieldGroup.style.display = movTipoSelect.value === 'SAIDA' ? '' : 'none';
      }
    }
    toggleEquipamentoField();
    movTipoSelect.addEventListener('change', toggleEquipamentoField);
  }

  // ===== 6. Movimentacao form: show current stock when item changes =====
  if (movItemSelect) {
    var stockDisplay = document.getElementById('current-stock');
    if (stockDisplay) {
      function updateStockDisplay() {
        var selectedOption = movItemSelect.options[movItemSelect.selectedIndex];
        var stock = selectedOption.getAttribute('data-stock');
        if (stock !== null) {
          stockDisplay.textContent = 'Saldo atual: ' + stock;
        } else {
          stockDisplay.textContent = '';
        }
      }
      updateStockDisplay();
      movItemSelect.addEventListener('change', updateStockDisplay);
    }
  }

  // ===== 7. Highlight rows where quantity < minimum =====
  document.querySelectorAll('.table-custom tbody tr').forEach(function (row) {
    if (row.classList.contains('row-alert')) {
      row.style.background = 'var(--row-alert-bg)';
    }
  });

  // ===== 8. Theme toggle with persistence =====
  var THEME_KEY = 'app_theme';
  var themeToggle = document.getElementById('theme-toggle');
  var html = document.documentElement;

  function getPreferredTheme() {
    var stored = localStorage.getItem(THEME_KEY);
    if (stored) return stored;
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }

  function setTheme(theme) {
    if (theme === 'dark') {
      html.setAttribute('data-theme', 'dark');
      if (themeToggle) themeToggle.innerHTML = '<i class="bi bi-sun-fill"></i>';
    } else {
      html.removeAttribute('data-theme');
      if (themeToggle) themeToggle.innerHTML = '<i class="bi bi-moon-fill"></i>';
    }
    localStorage.setItem(THEME_KEY, theme);
  }

  function toggleTheme() {
    var current = html.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    setTheme(current === 'dark' ? 'light' : 'dark');
  }

  // Apply saved theme on load
  setTheme(getPreferredTheme());

  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
  }

});
