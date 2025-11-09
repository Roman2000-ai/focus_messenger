
const QR_MODAL = document.getElementById('qrModal');
const QR_MODAL_CONTENT = document.getElementById('qr-modal-content');
const MODAL_TITLE = document.getElementById('modal-title');
const MODAL_DESCRIPTION = document.getElementById('modal-description');
const QR_STATUS_TEXT = document.getElementById('qr-status-text');
const QR_LOGIN_BTN = document.getElementById('qr-login-btn');
const QR_CANVAS = document.getElementById('qr-canvas');
const QR_SPINNER = document.getElementById('qr-spinner');
const TWO_FA_FORM = document.getElementById('two-fa-form');
const TWO_FA_INPUT = document.getElementById('2fa-password-input');

let pollingInterval = null;
let currentFlowId = null;

/**
    * Управляет видимостью элементов в модальном окне.
    */
function setModalContent(mode) {
    // Сброс всех скрываемых элементов
    QR_MODAL_CONTENT.classList.remove('show-qr-content');
    TWO_FA_FORM.style.display = 'none';
    QR_SPINNER.style.display = 'none';

    if (mode === 'loading') {
        QR_SPINNER.style.display = 'block';
        MODAL_TITLE.textContent = 'Инициализация';
        MODAL_DESCRIPTION.textContent = 'Получение ссылки QR-кода...';
        QR_STATUS_TEXT.textContent = 'Пожалуйста, подождите.';

    } else if (mode === 'qr') {
        QR_MODAL_CONTENT.classList.add('show-qr-content');
        MODAL_TITLE.textContent = 'Сканируйте QR-код';
        MODAL_DESCRIPTION.textContent = 'Откройте Telegram, перейдите в Настройки > Устройства > Подключить устройство.';
        QR_STATUS_TEXT.textContent = 'Ожидание сканирования...';

    } else if (mode === '2fa') {
        // Прячем QR-код, показываем форму 2FA
        MODAL_TITLE.textContent = 'Двухфакторная аутентификация';
        MODAL_DESCRIPTION.textContent = 'Пожалуйста, введите ваш пароль облачной безопасности Telegram.';
        TWO_FA_FORM.style.display = 'block';
        QR_STATUS_TEXT.textContent = 'Требуется пароль.';
        TWO_FA_INPUT.focus();
    }
}


/**
 * 1. Запускает QR-логин на бэкенде.
 * 2. Отображает модальное окно с QR-кодом.
 * 3. Запускает опрос статуса.
 */
async function startQrLogin() {
    // 🟢 ИЗМЕНЕНИЕ: Принудительный сброс формы 2FA и поля ввода
    TWO_FA_FORM.style.display = 'none'; 
    TWO_FA_INPUT.value = '';
    // ----------------------------------------------------
    
    QR_LOGIN_BTN.disabled = true;
    QR_MODAL.style.display = 'block';
    setModalContent('loading'); // Показываем спиннер

    try {
        // 1. Запрос на инициацию QR-логина
        const response = await fetch('/auth/qr', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        currentFlowId = data.flow_id;
        const qrUrl = data.qr_url;

        // 2. Отображаем QR-код
        await showQrCode(qrUrl);
        setModalContent('qr'); // Показываем QR-код

        // 3. Запускаем опрос
        startPolling();

    } catch (error) {
        setModalContent('loading'); 
        QR_STATUS_TEXT.textContent = `❌ Ошибка инициации: ${error.message}`;
        console.error("QR Start Error:", error);
        QR_LOGIN_BTN.disabled = false;
        
        // Автоматически закрываем модальное окно, если опрос не был запущен
        setTimeout(() => {
            if (pollingInterval === null) {
                QR_MODAL.style.display = 'none';
            }
        }, 3000);
    }
}

/**
    * Генерирует QR-код.
    */
function showQrCode(url) {
    return new Promise((resolve) => {
        const context = QR_CANVAS.getContext('2d');
        context.clearRect(0, 0, QR_CANVAS.width, QR_CANVAS.height);
        
        QRCode.toCanvas(QR_CANVAS, url, { width: 256, margin: 2 }, function (error) {
            if (error) {
                    console.error("QR Code Generation Error:", error);
                    QR_STATUS_TEXT.textContent = '❌ Не удалось создать QR-код.';
            }
            resolve();
        });
    });
}

/**
    * Запускает периодический опрос бэкенда.
    */
function startPolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    // Опрос каждые 2 секунды
    pollingInterval = setInterval(checkQrStatus, 2000);
}

/**
    * Останавливает опрос.
    */
function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

/**
    * Опрашивает бэкенд для проверки статуса QR-логина.
    */
async function checkQrStatus() {
    if (!currentFlowId) {
        console.error("Flow ID is missing, stopping polling.");
        stopPolling();
        return;
    }

    try {
        const response = await fetch('/auth/qr/check', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ flow_id: currentFlowId })
        });
        const data = await response.json();

        if (data.status === 'waiting') {
            QR_STATUS_TEXT.textContent = 'Ожидание сканирования...';

        } else if (data.status === 'authorized') {
            // УСПЕХ: Вход выполнен
            stopPolling();
            QR_STATUS_TEXT.textContent = '✅ Вход выполнен! Перенаправление...';
            
            if (data.redirect) {
                window.location.href = data.redirect;
            } else {
                setTimeout(closeQrModal, 3000);
            }
            
        } else if (data.status === '2fa_required') {
            // 🟢 НОВЫЙ СТАТУС: ТРЕБУЕТСЯ 2FA
            stopPolling(); // Останавливаем опрос QR-статуса
            promptFor2fa();

        } else if (data.status === 'error' || data.status === 'canceled') {
            // ОШИБКА / ОТМЕНА / ТАЙМАУТ
            stopPolling();
            QR_STATUS_TEXT.textContent = `❌ Ошибка: ${data.message || 'Процесс отменен.'}`;
            setTimeout(closeQrModal, 3000);
        }

    } catch (error) {
        stopPolling();
        QR_STATUS_TEXT.textContent = '❌ Ошибка соединения или парсинга ответа.';
        console.error("QR Check Error:", error);
        setTimeout(closeQrModal, 3000);
    }
}

/**
    * Показывает форму для ввода 2FA пароля.
    */
function promptFor2fa() {
    setModalContent('2fa');
    // Очищаем поле ввода от предыдущих попыток
    TWO_FA_INPUT.value = '';
}

/**
    * Отправляет 2FA пароль на бэкенд.
    * 🟢 ИЗМЕНЕНИЕ: Теперь явно принимает event и вызывает preventDefault().
    */
async function send2faPassword(event) {
    // 🟢 Предотвращаем стандартное действие формы (перезагрузку)
    if (event) {
        event.preventDefault(); 
    }
    
    console.log(`[2FA] Function called. Flow ID: ${currentFlowId}`); // Дополнительный лог для отладки

    const password = TWO_FA_INPUT.value;
    if (!password || !currentFlowId) {
        console.error("Missing password or flow ID. Cannot send 2FA.");
        return;
    }

    // Блокируем форму и показываем, что идет отправка
    const submitButton = TWO_FA_FORM.querySelector('button');
    submitButton.disabled = true;
    QR_STATUS_TEXT.textContent = 'Проверка пароля...';

    try {
        console.log("идет запрос на 2fa check")
        const response = await fetch('/auth/qr/2fa', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ flow_id: currentFlowId, password: password })
        });
        const data = await response.json();

        if (data.status === 'success') {
            // УСПЕХ: 2FA пройдена, вход завершен.
            QR_STATUS_TEXT.textContent = '✅ Пароль верный! Ожидание завершения сессии...';
            
            // Снова запускаем опрос, чтобы получить финальный статус 'authorized'
            setModalContent('loading'); 
            startPolling();
            
        } else if (data.status === '2fa_required') {
            // ОШИБКА: Неправильный пароль (бэкенд вернул, что 2FA все еще требуется)
            QR_STATUS_TEXT.textContent = `❌ ${data.message || 'Неправильный пароль.'} Повторите ввод.`;
            TWO_FA_INPUT.value = ''; // Очищаем поле
            TWO_FA_INPUT.focus();

        } else if (data.status === 'error') {
            // Критическая ошибка 2FA
            QR_STATUS_TEXT.textContent = `❌ Критическая ошибка: ${data.message || 'Сбой 2FA сессии.'}`;
            setTimeout(closeQrModal, 3000);
        }
        
        // Снова разблокируем форму, если это не терминальный статус
        if (data.status !== 'success' && data.status !== 'error') {
            submitButton.disabled = false;
        }
        
    } catch (error) {
        QR_STATUS_TEXT.textContent = '❌ Ошибка соединения при отправке пароля.';
        console.error("2FA Send Error:", error);
        submitButton.disabled = false;
    }
}

/**
    * Закрывает модальное окно и отправляет запрос на отмену сессии.
    */
async function closeQrModal() {
    stopPolling();
    QR_MODAL.style.display = 'none';
    QR_LOGIN_BTN.disabled = false;
    
    // Сбрасываем состояние модального окна на QR для следующего раза
    setModalContent('qr'); 

    if (currentFlowId) {
        // Отправляем запрос на бэкенд для очистки состояния
        try {
            await fetch('/auth/qr/cancel', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ flow_id: currentFlowId })
            });
            console.log(`[${currentFlowId}] Сессия отменена на бэкенде.`);
        } catch (error) {
            console.error("QR Cancel Error:", error);
        }
        currentFlowId = null;
    }
}
