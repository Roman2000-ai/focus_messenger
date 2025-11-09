



// --- НАСТРОЙКА AXIOS КЛИЕНТА С ЛОГИКОЙ REFRESH TOKEN ---

const apiClient = axios.create({

baseURL: '/', // Относительный путь

withCredentials: true, // Включаем отправку куки (токены)

headers: {

'Content-Type': 'application/json',

}

});



let isRefreshing = false;

let failedQueue = [];



// Функция для обработки запросов, ожидающих новый токен

const processQueue = (error, token = null) => {

failedQueue.forEach(prom => {

if (error) {

prom.reject(error);

} else {

// Разрешаем выполнение запросов, которые были поставлены на паузу

prom.resolve(token);

}

});

failedQueue = [];

};



// ** ГЛАВНЫЙ ПЕРЕХВАТЧИК **

apiClient.interceptors.response.use(

(response) => {

return response;

},

async (error) => {

const originalRequest = error.config;

const status = error.response ? error.response.status : null;


// 1. Проверяем, это ошибка 401 (Unauthorized) И это НЕ запрос на /refresh

if (status === 401 && originalRequest.url !== '/refresh') {


// Если мы уже пытаемся обновить токен, ставим этот запрос в очередь

if (isRefreshing) {

return new Promise((resolve, reject) => {

failedQueue.push({ resolve, reject });

})

.then(() => {

// Повторяем оригинальный запрос после получения нового токена

return apiClient(originalRequest);

})

.catch(err => {

return Promise.reject(err);

});

}



// 2. Начинаем процесс обновления токена

isRefreshing = true;


try {

// 3. Запрос нового токена. Браузер автоматически прикрепит refresh_token куку

await apiClient.post('auth/refresh');



isRefreshing = false;

processQueue(null); // Выполняем все ожидающие запросы


// 4. Повторяем исходный запрос, который вызвал 401

return apiClient(originalRequest);



} catch (refreshError) {

isRefreshing = false;

processQueue(refreshError, null); // Отклоняем ожидающие запросы


// 5. Если /refresh сам вернул 401 или другую ошибку,

// сессия полностью истекла -> ПЕРЕНАПРАВЛЕНИЕ НА ЛОГИН

console.error("Session expired or invalid. Redirecting to login.");

// Используем POST на /logout, чтобы очистить все куки на сервере


const form = document.createElement('form');

form.method = 'POST';

form.action = '/logout';

document.body.appendChild(form);

form.submit();


return Promise.reject(refreshError);

}

}


// Для всех остальных ошибок (400, 403, 5xx)

return Promise.reject(error);

}

);

// ----------------------------------------------------------------------





// ----------------------------------------------------

// 1) ЛОГИКА ОСНОВНОЙ СТРАНИЦЫ (активная сессия)

// (ВСЕ fetch ЗАМЕНЕНЫ НА apiClient)

// ----------------------------------------------------

(function setupMainWhenHasSession() {

// ... (Остальной код инициализации переменных: sendForm, contactSelect и т.д. - БЕЗ ИЗМЕНЕНИЙ) ...

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


// Загрузка сообщений (ИЗМЕНЕНИЕ: fetch заменен на apiClient)

async function loadMessagesForPeer(identifier) {

messagesHistoryDiv.innerHTML = '';

historyStatus.textContent = "Загрузка истории...";

historyStatus.style.display = 'block';


if (String(identifier).match(/^\d+$/)) {

historyStatus.textContent = "Невозможно загрузить историю, используя только ID. Пожалуйста, выберите контакт с @username.";

messagesHistoryDiv.innerHTML = '';

return;

}


try {

// ИСПОЛЬЗУЕМ apiClient ВМЕСТО fetch

const res = await apiClient.get(`telegram/messages/${identifier}`);

const data = res.data; // Axios: данные в свойстве .data


historyStatus.style.display = 'none';


if (data.success) {

// ... (логика обработки success - БЕЗ ИЗМЕНЕНИЙ) ...

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

// Здесь ловим ошибки сети, 5xx и 401, если refresh не удался

console.error("Fetch error:", error);

const detail = error.response && error.response.data && error.response.data.detail ? error.response.data.detail : 'Произошла ошибка сети при загрузке истории.';

messagesHistoryDiv.innerHTML = `<p style="color: var(--error-color);">Произошла ошибка: ${detail}</p>`;

}

}


// ... (логика saveSelectedPeer, restoreSelectedPeer, contactSelect.addEventListener - БЕЗ ИЗМЕНЕНИЙ) ...


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



document.addEventListener('DOMContentLoaded', restoreSelectedPeer);

if (document.readyState === 'interactive' || document.readyState === 'complete') {

restoreSelectedPeer();

}


// Логика Отправки сообщения (ИЗМЕНЕНИЕ: fetch заменен на apiClient)

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


const selectedValueBefore = selectedOption.value;

const selectedUsernameBefore = selectedOption.dataset.username || null;


const fd = new FormData(e.target);

const payload = { peer: peerIdentifier, message: fd.get('text') };


// ИСПОЛЬЗУЕМ apiClient ВМЕСТО fetch

const res = await apiClient.post('/telegram/send_message', payload);

const data = res.data;


// В Axios res.ok не нужен, так как 2xx коды попадают сюда.

if (data.success === true) {

showMessage("✅ Сообщение было успешно отправлено", 'success', statusMessage);

sendForm.reset();

manualPeerInput.style.display = 'none';

manualPeerInput.required = false;


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

} else {

const errorMessage = data.message || "Ошибка отправки сообщения Telegram.";

showMessage(`⚠️ ${errorMessage}`, 'error', statusMessage);

}

} catch (error) {

// Здесь ловим ошибки сети, 5xx и 401

console.error("Axios error:", error);

const errorDetail = error.response && error.response.data && error.response.data.detail ? error.response.data.detail : 'Произошла ошибка сети. Проверьте соединение.';

showMessage(`❌ Ошибка: ${errorDetail}`, 'error', statusMessage);

} finally {

setLoading(sendButton, false);

}

});


// Логика Добавления контакта (ИЗМЕНЕНИЕ: fetch заменен на apiClient)

if (addContactForm) {

addContactForm.addEventListener('submit', async (e) => {

e.preventDefault();

setLoading(addContactButton, true);


try {

const identifier = contactIdentifierInput.value;

const payload = { identifier: identifier };


// ИСПОЛЬЗУЕМ apiClient ВМЕСТО fetch

const res = await apiClient.post('telegram/add_contact', payload);

const data = res.data;


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

console.error("Add Contact Axios error:", error);

const errorDetail = error.response && error.response.data && error.response.data.detail ? error.response.data.detail : 'Произошла ошибка сети при добавлении контакта.';

showMessage(`🛑 Произошла ошибка: ${errorDetail}`, 'error', addContactStatusMessage);

} finally {

setLoading(addContactButton, false);

}

});

}

})();


// ----------------------------------------------------

// 2) ЛОГИКА АВТОРИЗАЦИИ (нет активной сессии)

// (Не меняем на apiClient, т.к. эти эндпоинты не защищены access_token'ом)

// ----------------------------------------------------

(function setupAuthWhenNoSession() {

const startForm = document.getElementById('phone-start');

const codeForm = document.getElementById('phone-code');

const pwdForm = document.getElementById('phone-pwd');


// ... (весь код setupAuthWhenNoSession остался БЕЗ ИЗМЕНЕНИЙ,

// так как авторизация не зависит от access_token и не требует refresh-логики) ...

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