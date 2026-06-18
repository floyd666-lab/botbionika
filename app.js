let tg = window.Telegram.WebApp;

// Расширяем Mini App на весь экран
tg.expand();

// Настройка цвета Header в Telegram (чтобы совпадало с нашим дизайном)
tg.setHeaderColor('#0F172A');
tg.setBackgroundColor('#0F172A');

const form = document.getElementById('orderForm');
const materialsInput = document.getElementById('materials');
const objectInput = document.getElementById('objectName');
const productInput = document.getElementById('productName');
const submitBtn = document.getElementById('submitBtn');

// Валидация полей
function validateField(input, minLength) {
    const value = input.value.trim();
    const formGroup = input.closest('.form-group');
    
    if (value.length < minLength) {
        formGroup.classList.add('has-error');
        return false;
    } else {
        formGroup.classList.remove('has-error');
        return true;
    }
}

// При вводе снимаем ошибку
[materialsInput, objectInput, productInput].forEach(input => {
    input.addEventListener('input', () => {
        input.closest('.form-group').classList.remove('has-error');
    });
});

submitBtn.addEventListener('click', (e) => {
    e.preventDefault();
    
    const isMaterialsValid = validateField(materialsInput, 10);
    const isObjectValid = validateField(objectInput, 2);
    const isProductValid = validateField(productInput, 2);
    
    if (isMaterialsValid && isObjectValid && isProductValid) {
        // Делаем кнопку неактивной, чтобы не было двойных кликов
        submitBtn.disabled = true;
        submitBtn.querySelector('span').textContent = 'Отправка...';
        
        // Собираем данные
        const data = {
            materials: materialsInput.value.trim(),
            object: objectInput.value.trim(),
            product: productInput.value.trim()
        };
        
        // Отправляем данные обратно боту
        tg.sendData(JSON.stringify(data));
    }
});
