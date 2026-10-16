const rolSelect = document.getElementById('id_rol');
    const typeDocContainer = document.getElementById('container_tipo_documento');
    const typeDocSelect = document.getElementById('id_tipo_documento');
    const labelCedula = document.getElementById('label_cedula');

    function updateDocFields() {
      const rol = rolSelect.value;
      const sectorCont = document.getElementById('container_empresa_sector');
      const ciudadCont = document.getElementById('container_empresa_ciudad');
      if (rol === 'empresa') {
        typeDocContainer.style.display = 'block';
        if (sectorCont) sectorCont.style.display = 'block';
        if (ciudadCont) ciudadCont.style.display = 'block';
        labelCedula.innerText = 'NIT O NÚMERO DE IDENTIFICACIÓN';
      } else {
        typeDocContainer.style.display = 'none';
        if (sectorCont) sectorCont.style.display = 'none';
        if (ciudadCont) ciudadCont.style.display = 'none';
        if (typeDocSelect) typeDocSelect.value = 'cedula';
        labelCedula.innerText = 'NÚMERO DE IDENTIFICACIÓN';
      }
    }

    // ── Role cards ──
    const roleCards = document.querySelectorAll('.role-card');
    roleCards.forEach(card => {
      card.addEventListener('click', function() {
        roleCards.forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        rolSelect.value = this.dataset.role;
        rolSelect.dispatchEvent(new Event('change'));
        var wrapper = document.querySelector('.register-wrapper');
        if (wrapper) wrapper.classList.toggle('theme-dev', this.dataset.role === 'desarrollador');
      });
    });

    rolSelect.addEventListener('change', updateDocFields);
    window.addEventListener('load', updateDocFields);

    document.querySelector('form').addEventListener('submit', function(e) {
      const password1 = document.querySelector('input[name="password1"]').value;
      const password2 = document.querySelector('input[name="password2"]').value;

      if (password1 !== password2) {
        e.preventDefault();
        alert('Las contraseñas ingresadas no coinciden. Verifícalas y vuelve a intentar.');
        return;
      }
    });
