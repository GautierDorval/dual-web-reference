// Progressive enhancement only: tables are complete without this script.
// Filters hide rows, headers sort rows, and the state lives in the URL fragment.
(function () {
  'use strict';
  function readState() {
    var state = {};
    var hash = window.location.hash.replace(/^#/, '');
    if (!hash || hash.indexOf('=') < 0) return state;
    hash.split('&').forEach(function (pair) {
      var parts = pair.split('=');
      if (parts.length === 2) state[decodeURIComponent(parts[0])] = decodeURIComponent(parts[1]);
    });
    return state;
  }
  function writeState(state) {
    var parts = Object.keys(state).sort().filter(function (key) { return state[key]; }).map(function (key) {
      return encodeURIComponent(key) + '=' + encodeURIComponent(state[key]);
    });
    var url = window.location.pathname + window.location.search + (parts.length ? '#' + parts.join('&') : '');
    window.history.replaceState(null, '', url);
  }
  var state = readState();
  document.querySelectorAll('form.filters').forEach(function (form) {
    var tableId = form.getAttribute('data-table');
    var table = document.getElementById(tableId);
    if (!table) return;
    var selects = form.querySelectorAll('select[data-filter]');
    var output = form.querySelector('output');
    function apply() {
      var shown = 0;
      var rows = table.tBodies[0].rows;
      for (var i = 0; i < rows.length; i++) {
        var visible = true;
        selects.forEach(function (select) {
          var value = select.value;
          if (value && rows[i].getAttribute('data-' + select.getAttribute('data-filter')) !== value) visible = false;
        });
        rows[i].hidden = !visible;
        if (visible) shown++;
      }
      if (output) output.textContent = shown + ' / ' + rows.length;
    }
    selects.forEach(function (select) {
      var key = tableId + '.' + select.getAttribute('data-filter');
      if (state[key]) select.value = state[key];
      select.addEventListener('change', function () {
        state[key] = select.value;
        writeState(state);
        apply();
      });
    });
    apply();
  });
  document.querySelectorAll('table.data').forEach(function (table) {
    var headers = table.tHead ? table.tHead.rows[0].cells : [];
    Array.prototype.forEach.call(headers, function (header, index) {
      var button = header.querySelector('button.sort');
      if (!button) return;
      button.addEventListener('click', function () {
        var ascending = header.getAttribute('aria-sort') !== 'ascending';
        Array.prototype.forEach.call(headers, function (other) { other.removeAttribute('aria-sort'); });
        header.setAttribute('aria-sort', ascending ? 'ascending' : 'descending');
        var body = table.tBodies[0];
        var rows = Array.prototype.slice.call(body.rows);
        rows.forEach(function (row, position) { row.setAttribute('data-order', position); });
        rows.sort(function (a, b) {
          var x = a.cells[index].getAttribute('data-value');
          var y = b.cells[index].getAttribute('data-value');
          var nx = parseFloat(x), ny = parseFloat(y);
          var result = (!isNaN(nx) && !isNaN(ny)) ? nx - ny : String(x).localeCompare(String(y));
          if (result === 0) result = Number(a.getAttribute('data-order')) - Number(b.getAttribute('data-order'));
          return ascending ? result : -result;
        });
        rows.forEach(function (row) { body.appendChild(row); });
      });
    });
  });
})();
