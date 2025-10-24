// ======================================================================
// index.js — объединённый файл без изменения логики
// 1) Логика основной страницы (есть активная сессия): отправка, история, контакты
// 2) Логика авторизации (нет активной сессии)
// 3) Кнопка выхода
// Все обработчики навешиваются ТОЛЬКО если нужные элементы присутствуют на странице
// ======================================================================

// ----------------------------------------------------
// 1) ЛОГИКА ОСНОВНОЙ СТРАНИЦЫ (активная сессия)
//    (перенесено из блока {% if has_session %} ... {% endif %})
// ----------------------------------------------------
(function setupMainWhenHasSession() {
    const sendForm = document.getElementById('send-form');
    const sendButton = document.getElementById('send-button');
    const statusMessage = document.getElementById('status-message');
    const contactSelect = document.getElementById('contact-select');
    const manualPeerInput = document.getElementById('manual-peer-input');
  
    const addContactForm = document.getElementById('add-contact-form');
    const addContactButton = document.getElementById('add-contact-button');
    const addContactStatusMessage = document.getElementById('add-contact-status-message');
    const contactIdentifierInput = document.getElementById('contact-identifier-input');
  
    const messagesHistoryDiv = document.getElementById('messages-history');
    const historyStatus = document.getElementById('history-status');
  
    // Если нет ключевых элементов — значит мы на странице без активной сессии. Ничего не делаем.
    if (!sendForm || !contactSelect) return;
  
    // --- Утилиты (без изменений)
    function showMessage(text, type = 'success', targetElement = statusMessage) {
      targetElement.textContent = text;
      targetElement.className = `status-${type}`;
      targetElement.style.display = 'block';
      setTimeout(() => {
        targetElement.style.display = 'none';
      }, 5000);
    }
  
    function setLoading(button, isLoading) {
      button.disabled = isLoading;
      const originalText = button.dataset.originalText || button.textContent;
      button.dataset.originalText = originalText;
  
      if (isLoading) {
        button.innerHTML = '<span class="spinner"></span> Обработка...';
      } else {
        button.innerHTML = originalText;
      }
    }
  
    // Динамически добавляет новый контакт в выпадающий список.
    function addContactToSelect(contact) {
      const manualOption = contactSelect.querySelector('option[value="manual_input"]');
  
      const newOption = document.createElement('option');
      newOption.value = contact.telegram_id;
  
      if (contact.username) {
        newOption.dataset.username = contact.username;
      }
  
      newOption.textContent = `${contact.first_name || 'Без имени'} ${contact.last_name || ''} (${contact.username ? '@' + contact.username : contact.telegram_id})`;
  
      if (manualOption) {
        contactSelect.insertBefore(newOption, manualOption);
      } else {
        contactSelect.appendChild(newOption);
      }
  
      newOption.selected = true;
    }
  
    // Загрузка сообщений (без изменений)
    async function loadMessagesForPeer(identifier) {
      messagesHistoryDiv.innerHTML = '';
      historyStatus.textContent = "Загрузка истории...";
      historyStatus.style.display = 'block';
  
      // Эндпоинт ожидает @username (строку), поэтому не передаем чистый ID
      if (String(identifier).match(/^\d+$/)) {
        historyStatus.textContent = "Невозможно загрузить историю, используя только ID. Пожалуйста, выберите контакт с @username.";
        return;
      }
  
      try {
        const res = await fetch(`/messages/${identifier}`, {
          method: 'GET',
          credentials: 'include'
        });
        const data = await res.json();
  
        historyStatus.style.display = 'none';
  
        if (data.success) {
          const messages = data.messages;
  
          function convertUTCToLocal(dateString) {
            try {
              const utcDate = new Date(dateString.replace(' UTC', 'Z'));
              const hours = String(utcDate.getHours()).padStart(2, '0');
              const minutes = String(utcDate.getMinutes()).padStart(2, '0');
              return `${hours}:${minutes}`;
            } catch (e) {
              console.warn("Ошибка преобразования даты:", dateString, e);
              return dateString;
            }
          }
  
          if (messages.length === 0) {
            messagesHistoryDiv.innerHTML = '<p style="color: #888;">Нет отправленных сообщений за последние 12 часов.</p>';
          } else {
            let html = messages.reverse().map(msg => {
              const localTime = convertUTCToLocal(msg.date);
              return `
                <div style="margin-bottom: 8px; border-bottom: 1px dashed #eee;">
                  <small style="color: var(--tg-color); font-weight: 600;">${localTime}</small>
                  <p style="margin: 0; word-wrap: break-word;">${msg.text}</p>
                </div>`;
            }).join('');
            messagesHistoryDiv.innerHTML = html;
            messagesHistoryDiv.scrollTop = messagesHistoryDiv.scrollHeight;
          }
        } else {
          messagesHistoryDiv.innerHTML = `<p style="color: var(--error-color);">Ошибка загрузки: ${data.message || 'Неизвестная ошибка.'}</p>`;
        }
  
      } catch (error) {
        console.error("Fetch error:", error);
        messagesHistoryDiv.innerHTML = '<p style="color: var(--error-color);">Произошла ошибка сети при загрузке истории.</p>';
      }
    }
  
    // Сохранение выбранного чата между сессиями (без изменений)
    function saveSelectedPeer(identifier) {
      localStorage.setItem('last_selected_peer', identifier);
    }
  
    function restoreSelectedPeer() {
      const savedPeer = localStorage.getItem('last_selected_peer');
      if (!savedPeer) return;
  
      const optionToSelect = Array.from(contactSelect.options).find(option =>
        option.dataset.username === savedPeer || option.value === savedPeer
      );
  
      if (optionToSelect) {
        optionToSelect.selected = true;
        if (optionToSelect.dataset.username) {
          loadMessagesForPeer(savedPeer);
        } else {
          historyStatus.textContent = "История доступна только для контактов с @username.";
        }
      } else {
        localStorage.removeItem('last_selected_peer');
      }
    }
  
    // Логика переключения ввода контакта (добавили сохранение)
    contactSelect.addEventListener('change', (e) => {
      const selectedOption = contactSelect.options[contactSelect.selectedIndex];
      let identifierToLoad = null;
  
      if (e.target.value === 'manual_input') {
        manualPeerInput.style.display = 'block';
        manualPeerInput.required = true;
        manualPeerInput.focus();
        historyStatus.textContent = "Введите @username или ID вручную, чтобы отправить.";
        messagesHistoryDiv.innerHTML = '';
  
        localStorage.removeItem('last_selected_peer');
  
      } else {
        manualPeerInput.style.display = 'none';
        manualPeerInput.required = false;
  
        identifierToLoad = selectedOption.dataset.username || selectedOption.value;
  
        saveSelectedPeer(identifierToLoad);
  
        if (selectedOption.dataset.username) {
          loadMessagesForPeer(identifierToLoad);
        } else {
          historyStatus.textContent = "История загружается только для контактов с @username.";
          messagesHistoryDiv.innerHTML = '';
        }
      }
    });
  
    // Восстановление выбранного чата при загрузке страницы
    document.addEventListener('DOMContentLoaded', restoreSelectedPeer);
    if (document.readyState === 'interactive' || document.readyState === 'complete') {
      restoreSelectedPeer();
    }
  
    // Логика Отправки сообщения (без изменений КРОМЕ фикса сохранения выбора)
    sendForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      setLoading(sendButton, true);
  
      try {
        const selectedOption = contactSelect.options[contactSelect.selectedIndex];
        let peerIdentifier;
  
        if (selectedOption.value === 'manual_input') {
          peerIdentifier = manualPeerInput.value;
        } else {
          const username = selectedOption.dataset.username;
          peerIdentifier = username || selectedOption.value;
        }
  
        if (!peerIdentifier) {
          showMessage("⚠️ Не выбран контакт или не введен идентификатор.", 'error', statusMessage);
          setLoading(sendButton, false);
          return;
        }
  
        // --- FIX: запоминаем текущий выбор, чтобы восстановить после reset() ---
        const selectedValueBefore = selectedOption.value;
        const selectedUsernameBefore = selectedOption.dataset.username || null;
        // ----------------------------------------------------------------------
  
        const fd = new FormData(e.target);
        const payload = { peer: peerIdentifier, message: fd.get('text') };
  
        const res = await fetch('/telegram/send_message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload)
        });
  
        const data = await res.json();
  
        if (res.ok) {
          if (data.success === true) {
            showMessage("✅ Сообщение было успешно отправлено", 'success', statusMessage);
            sendForm.reset();
            manualPeerInput.style.display = 'none';
            manualPeerInput.required = false;
  
            // --- FIX: возвращаем выбор контакта и обновляем историю/локалсторадж ---
            let toSelect = Array.from(contactSelect.options).find(opt =>
              (selectedUsernameBefore && opt.dataset.username === selectedUsernameBefore) ||
              (!selectedUsernameBefore && opt.value === selectedValueBefore)
            );
            if (toSelect) {
              toSelect.selected = true;
              const ident = selectedUsernameBefore || selectedValueBefore;
              saveSelectedPeer(ident);
              if (selectedUsernameBefore) {
                loadMessagesForPeer(selectedUsernameBefore);
              }
            }
            // ----------------------------------------------------------------------
  
          } else {
            const errorMessage = data.message || "Ошибка отправки сообщения Telegram.";
            showMessage(`⚠️ ${errorMessage}`, 'error', statusMessage);
          }
        } else {
          const errorDetail = data && data.detail ? data.detail : 'Неизвестная ошибка сети или сервера.';
          showMessage(`❌ Ошибка HTTP ${res.status}: ${errorDetail}`, 'error', statusMessage);
        }
      } catch (error) {
        console.error("Fetch error:", error);
        showMessage("🛑 Произошла ошибка сети. Проверьте соединение.", 'error', statusMessage);
      } finally {
        setLoading(sendButton, false);
      }
    });
  
    // Логика Добавления контакта (без изменений)
    if (addContactForm) {
      addContactForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        setLoading(addContactButton, true);
  
        try {
          const identifier = contactIdentifierInput.value;
  
          const res = await fetch('/add_contact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ identifier: identifier })
          });
  
          const data = await res.json();
  
          if (data.success) {
            const contact = data.contact;
            showMessage(`✅ Контакт ${contact.username ? '@' + contact.username : contact.telegram_id} успешно добавлен/обновлен.`, 'success', addContactStatusMessage);
            addContactForm.reset();
            addContactToSelect(contact);
          } else {
            const errorMessage = data.message || 'Не удалось добавить контакт.';
            showMessage(`❌ Ошибка: ${errorMessage}`, 'error', addContactStatusMessage);
          }
        } catch (error) {
          console.error("Add Contact Fetch error:", error);
          showMessage("🛑 Произошла ошибка сети при добавлении контакта.", 'error', addContactStatusMessage);
        } finally {
          setLoading(addContactButton, false);
        }
      });
    }
  })();
  
  // ----------------------------------------------------
  // 2) ЛОГИКА АВТОРИЗАЦИИ (нет активной сессии)
  //    (перенесено из блока {% else %} ... {% endif %})
  // ----------------------------------------------------
  (function setupAuthWhenNoSession() {
    const startForm = document.getElementById('phone-start');
    const codeForm  = document.getElementById('phone-code');
    const pwdForm   = document.getElementById('phone-pwd');
  
    // Если этих форм нет — значит мы на странице с активной сессией.
    if (!startForm || !codeForm || !pwdForm) return;
  
    function showAuthMessage(text, type = 'error') {
      const status = document.getElementById('status-message');
      status.textContent = text;
      status.className = `status-${type}`;
      status.style.display = 'block';
      if (type !== 'error') {
        setTimeout(() => status.style.display = 'none', 5000);
      }
    }
  
    function setAuthLoading(formId, isLoading) {
      const button = document.getElementById(formId).querySelector('button[type="submit"]');
      button.disabled = isLoading;
      if (isLoading) {
        button.innerHTML = '<span class="spinner"></span> Обработка...';
      } else {
        if (formId === 'phone-start') button.innerHTML = 'Отправить код';
        if (formId === 'phone-code') button.innerHTML = 'Подтвердить код';
        if (formId === 'phone-pwd') button.innerHTML = 'Подтвердить пароль';
      }
    }
  
    startForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      setAuthLoading('phone-start', true);
      const phone = new FormData(startForm).get('phone');
  
      try {
        const res = await fetch('/auth/phone/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ phone })
        });
        const data = await res.json();
  
        if (!res.ok) {
          showAuthMessage(data.detail || 'Ошибка при отправке номера телефона');
          return;
        }
  
        showAuthMessage('✅ Код отправлен в Telegram. Введите его ниже.', 'success');
        codeForm.style.display = 'flex';
        codeForm.querySelector('[name=flow_id]').value = data.flow_id;
        startForm.style.display = 'none';
  
      } catch (error) {
        showAuthMessage('🛑 Произошла ошибка сети. Проверьте соединение.');
      } finally {
        setAuthLoading('phone-start', false);
      }
    });
  
    codeForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      setAuthLoading('phone-code', true);
      const fd = new FormData(codeForm);
      const payload = { flow_id: fd.get('flow_id'), code: fd.get('code') };
  
      try {
        const res = await fetch('/auth/phone/verify_code', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload)
        });
        const data = await res.json();
  
        if (!res.ok) {
          showAuthMessage(data.detail || 'Ошибка при подтверждении кода');
          return;
        }
  
        if (data.need_2fa) {
          showAuthMessage('🔑 Требуется двухфакторная аутентификация. Введите пароль.');
          pwdForm.style.display = 'flex';
          pwdForm.querySelector('[name=flow_id]').value = payload.flow_id;
          codeForm.style.display = 'none';
        } else {
          location.reload(); // Успех
        }
      } catch (error) {
        showAuthMessage('🛑 Произошла ошибка сети. Проверьте соединение.');
      } finally {
        setAuthLoading('phone-code', false);
      }
    });
  
    pwdForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      setAuthLoading('phone-pwd', true);
      const fd = new FormData(pwdForm);
      const payload = { flow_id: fd.get('flow_id'), password: fd.get('password') };
  
      try {
        const res = await fetch('/auth/phone/verify_password', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify(payload)
        });
        const data = await res.json();
  
        if (!res.ok) {
          showAuthMessage(data.detail || 'Ошибка при подтверждении пароля');
          return;
        }
  
        location.reload(); // Успех
  
      } catch (error) {
        showAuthMessage('🛑 Произошла ошибка сети. Проверьте соединение.');
      } finally {
        setAuthLoading('phone-pwd', false);
      }
    });
  })();
  
  // ----------------------------------------------------
  // 3) ВЫХОД ИЗ СЕССИИ (точно такая же логика, только вынесена)
  // ----------------------------------------------------
  (function setupLogout() {
    const logOutButton = document.getElementById("log_out");
    if (!logOutButton) return;
  
    logOutButton.onclick = function () {
      const form = document.createElement('form');
      form.method = 'POST';
      form.action = '/logout';
      document.body.appendChild(form);
      form.submit();
    };
  })();
  