(() => {
    'use strict';
    const board = document.getElementById('kanban-board');
    if (!board) return;
    const cards = [...board.querySelectorAll('[data-ticket]')];
    const columns = [...board.querySelectorAll('.kanban-column')];
    const feedback = board.querySelector('.kanban-feedback');
    const message = document.getElementById('kanban-message');
    const refresh = document.getElementById('kanban-refresh');
    let dragged = null;
    let saving = false;
    function announce(text, kind = '', needsRefresh = false) {
        message.textContent = text;
        feedback.classList.toggle('is-error', kind === 'error');
        feedback.classList.toggle('is-success', kind === 'success');
        refresh.hidden = !needsRefresh;
    }
    function updateCounts() {
        columns.forEach(column => {
            const count = column.querySelectorAll('[data-ticket]').length;
            column.querySelector('.kanban-count').textContent = count;
            column.querySelector('.kanban-empty').hidden = count > 0;
            column.classList.remove('is-over');
        });
    }
    function setBusy(value) {
        saving = value;
        board.setAttribute('aria-busy', String(value));
        cards.forEach(card => {
            card.draggable = !value;
            card.querySelectorAll('button, select').forEach(control => { control.disabled = value; });
        });
    }
    async function move(card, state) {
        if (saving) return;
        const form = card.querySelector('form');
        const previous = card.dataset.state;
        const select = form.elements.estado;
        const target = columns.find(column => column.dataset.state === state);
        if (!target) return;
        if (previous === state) { announce('El ticket ya está en esa columna.'); return; }
        const hadFocus = card.contains(document.activeElement);
        const data = new URLSearchParams({estado: state, estado_anterior: previous});
        setBusy(true);
        card.classList.add('is-saving');
        announce(`Guardando el ticket ${card.dataset.ticket}…`);
        const controller = new AbortController();
        const timeout = window.setTimeout(() => controller.abort(), 20000);
        try {
            const response = await fetch(form.action, {
                method: 'POST', credentials: 'same-origin', redirect: 'error',
                signal: controller.signal,
                headers: {'Accept': 'application/json', 'X-CSRFToken': form.elements.csrfmiddlewaretoken.value},
                body: data,
            });
            const result = (response.headers.get('content-type') || '').includes('application/json')
                ? await response.json() : {};
            if (!response.ok) throw new Error(result.error || (response.status === 403
                ? 'No se pudo autorizar el cambio. Actualice el tablero y vuelva a intentarlo.'
                : 'No se pudo guardar el cambio. Actualice el tablero para comprobar el estado.'));
            if (result.estado !== state || result.ticket !== card.dataset.ticket)
                throw new Error('La respuesta no coincide con el cambio. Actualice el tablero para comprobar el estado.');
            target.querySelector('[data-dropzone]').insertBefore(card, target.querySelector('.kanban-empty'));
            card.dataset.state = result.estado;
            form.elements.estado_anterior.value = result.estado;
            select.value = result.estado;
            const age = card.querySelector('.kanban-age');
            age.className = 'badge kanban-age ' + (state === 'Resuelto' ? 'text-bg-success' : age.dataset.ageClass);
            age.textContent = state === 'Resuelto' ? 'Cerrado' : `Día ${age.dataset.days}`;
            updateCounts();
            announce(`Ticket ${result.ticket} movido a ${target.querySelector('h2').textContent}. Cambio guardado.`, 'success');
        } catch (error) {
            select.value = previous;
            announce(error instanceof TypeError || error.name === 'AbortError'
                ? 'Se perdió la conexión. Actualice el tablero para comprobar si el cambio se guardó.' : error.message,
                'error', true);
        } finally {
            window.clearTimeout(timeout);
            card.classList.remove('is-saving');
            setBusy(false);
            if (hadFocus) select.focus();
            updateCounts();
        }
    }
    cards.forEach(card => {
        card.draggable = true;
        card.addEventListener('dragstart', event => {
            if (saving || event.target.closest('a, button, select, input')) { event.preventDefault(); return; }
            dragged = card;
            card.classList.add('is-dragging');
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', card.dataset.ticket);
        });
        card.addEventListener('dragend', () => {
            dragged = null;
            card.classList.remove('is-dragging');
            columns.forEach(column => column.classList.remove('is-over'));
        });
        card.querySelector('form').addEventListener('submit', event => {
            event.preventDefault();
            move(card, event.currentTarget.elements.estado.value);
        });
    });
    columns.forEach(column => {
        column.addEventListener('dragover', event => {
            if (!dragged || saving || column.dataset.state === dragged.dataset.state) return;
            event.preventDefault();
            event.dataTransfer.dropEffect = 'move';
            column.classList.add('is-over');
        });
        column.addEventListener('dragleave', event => {
            if (!column.contains(event.relatedTarget)) column.classList.remove('is-over');
        });
        column.addEventListener('drop', event => {
            if (!dragged || saving) return;
            event.preventDefault();
            const card = dragged;
            dragged = null;
            card.classList.remove('is-dragging');
            columns.forEach(item => item.classList.remove('is-over'));
            move(card, column.dataset.state);
        });
    });
    refresh.addEventListener('click', () => window.location.reload());
})();
