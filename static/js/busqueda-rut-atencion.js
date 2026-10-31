(() => {
    const input=document.querySelector('[data-buscar-vecino]');
    const select=document.querySelector('[data-selector-vecino]');
    if (!input || !select) return;
    const normalize=value=>value.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
    const compact=value=>normalize(value).replace(/[^a-z0-9]/g,'');
    const options=[...select.options].map(option=>({option,label:normalize(option.textContent)}));
    const status=document.createElement('div');
    status.className='form-text';
    status.setAttribute('role','status');
    status.setAttribute('aria-live','polite');
    input.after(status);
    input.addEventListener('input',()=>{
        const query=normalize(input.value.trim());
        const rut=/^[\d.\s-]+[\dk]?$/.test(query);
        let matches=[];
        options.forEach(({option,label})=>{
            const match=!query || (rut ? compact(label).includes(compact(query)) : query.split(/\s+/).every(word=>label.includes(word)));
            option.hidden=Boolean(option.value && !match);
            if (option.value && match) matches.push(option);
        });
        if (query && matches.length===1) {
            select.value=matches[0].value;
            select.dispatchEvent(new Event('change',{bubbles:true}));
        } else if (query) {
            select.value='';
        }
        status.textContent=query ? (matches.length ? `${matches.length} vecino(s) encontrado(s). Selecciona el que corresponda.` : 'No se encontraron vecinos con ese RUT o nombre.') : '';
    });
})();
