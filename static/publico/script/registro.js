// Textos traducidos por el template (ver el bloque #textos-i18n).
    const TEXTOS = (function () {
      const nodo = document.getElementById('textos-i18n');
      if (!nodo) return {};
      try { return JSON.parse(nodo.textContent) || {}; } catch (e) { return {}; }
    })();

    function texto(clave, porDefecto) {
      const valor = TEXTOS[clave];
      return (typeof valor === 'string' && valor) ? valor : porDefecto;
    }

    const rolSelect = document.getElementById('id_rol');
    const typeDocContainer = document.getElementById('container_tipo_documento');
    const typeDocSelect = document.getElementById('id_tipo_documento');
    const labelCedula = document.getElementById('label_cedula');
    const identInput = document.getElementById('id_identificacion');

    function updateDocLabel() {
      if (!labelCedula || !typeDocSelect) return;
      const tipo = typeDocSelect.value;
      if (tipo === 'nit') {
        labelCedula.innerText = texto('docNit', 'NIT');
        if (identInput) identInput.placeholder = 'Ej: 900123456-7';
      } else if (tipo === 'ti') {
        labelCedula.innerText = texto('docTi', 'TARJETA DE IDENTIDAD');
        if (identInput) identInput.placeholder = 'Ej: 1002345678';
      } else {
        labelCedula.innerText = texto('docNumero', 'CÉDULA DE CIUDADANÍA');
        if (identInput) identInput.placeholder = 'Ej: 1002345678';
      }
    }

    if (typeDocSelect) {
      typeDocSelect.addEventListener('change', updateDocLabel);
    }

    function updateDocOptionsForRole(rol) {
      if (!typeDocSelect) return;
      const allowed = rol === 'empresa' ? ['nit', 'cedula'] : ['cedula', 'ti'];
      Array.from(typeDocSelect.options).forEach(opt => {
        const ok = allowed.includes(opt.value);
        opt.hidden = !ok;
        opt.disabled = !ok;
      });
      if (!allowed.includes(typeDocSelect.value)) {
        typeDocSelect.value = allowed[0];
      }
    }

    function updateDocFields() {
      const rol = rolSelect.value;
      const sectorCont = document.getElementById('container_empresa_sector');
      const ciudadCont = document.getElementById('container_empresa_ciudad');
      const academicoCont = document.getElementById('container_desarrollador_academico');
      if (typeDocContainer) typeDocContainer.style.display = 'block';
      updateDocOptionsForRole(rol);
      if (rol === 'empresa') {
        if (sectorCont) sectorCont.style.display = 'block';
        if (ciudadCont) ciudadCont.style.display = 'block';
        if (academicoCont) academicoCont.style.display = 'none';
      } else {
        if (sectorCont) sectorCont.style.display = 'none';
        if (ciudadCont) ciudadCont.style.display = 'none';
        if (academicoCont) academicoCont.style.display = 'grid';
      }
      updateDocLabel();
    }

    // ── Role cards ──
    const roleCards = document.querySelectorAll('.role-card');
    roleCards.forEach(card => {
      card.addEventListener('click', function() {
        const nextRole = this.dataset.role;
        const roleChanged = rolSelect.value !== nextRole;
        roleCards.forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        rolSelect.value = nextRole;
        if (roleChanged && typeDocSelect) {
          typeDocSelect.value = nextRole === 'empresa' ? 'nit' : 'cedula';
        }
        rolSelect.dispatchEvent(new Event('change'));
        var wrapper = document.querySelector('.register-wrapper');
        if (wrapper) wrapper.classList.toggle('theme-dev', nextRole === 'desarrollador');
      });
    });

    rolSelect.addEventListener('change', updateDocFields);
    window.addEventListener('load', updateDocFields);

    document.querySelector('form').addEventListener('submit', function(e) {
      const password1 = document.querySelector('input[name="password1"]').value;
      const password2 = document.querySelector('input[name="password2"]').value;

      if (password1 !== password2) {
        e.preventDefault();
        alert(texto('passwordMismatch', 'Las contraseñas ingresadas no coinciden. Verifícalas y vuelve a intentar.'));
        return;
      }
    });
