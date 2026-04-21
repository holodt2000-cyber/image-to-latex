const uploadArea = document.getElementById('uploadArea');
const imageInput = document.getElementById('imageInput');
const preview = document.getElementById('preview');
const previewImage = document.getElementById('previewImage');
const convertBtn = document.getElementById('convertBtn');
const loading = document.getElementById('loading');
const result = document.getElementById('result');
const latexOutput = document.getElementById('latexOutput');
const latexPreview = document.getElementById('latexPreview');
const copyBtn = document.getElementById('copyBtn');

let selectedFile = null;

// Click to upload
uploadArea.addEventListener('click', () => {
    imageInput.click();
});

// File selection
imageInput.addEventListener('change', (e) => {
    handleFile(e.target.files[0]);
});

// Drag and drop
uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    handleFile(e.dataTransfer.files[0]);
});

// Paste from clipboard
document.addEventListener('paste', (e) => {
    const items = e.clipboardData.items;

    for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
            e.preventDefault();
            const blob = items[i].getAsFile();
            handleFile(blob);
            break;
        }
    }
});

// Вставь это в любое место вне других функций
async function compressImage(file) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = (event) => {
            const img = new Image();
            img.src = event.target.result;
            img.onload = () => {
                const canvas = document.createElement('canvas');
                const MAX_WIDTH = 1200; // Оптимально для Gemini 2.5 Flash
                let width = img.width;
                let height = img.height;

                if (width > MAX_WIDTH) {
                    height *= MAX_WIDTH / width;
                    width = MAX_WIDTH;
                }
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                
                canvas.toBlob((blob) => {
                    resolve(blob);
                }, 'image/jpeg', 0.8); // 80% качества — идеально для ИИ
            };
        };
    });
}


function handleFile(file) {
    if (!file || !file.type.startsWith('image/')) {
        alert('Пожалуйста, выберите изображение');
        return;
    }

    selectedFile = file;

    const reader = new FileReader();
    reader.onload = (e) => {
        previewImage.src = e.target.result;
        preview.classList.remove('hidden');
        convertBtn.classList.remove('hidden');
        result.classList.add('hidden');
    };
    reader.readAsDataURL(file);
}

// Convert button
convertBtn.addEventListener('click', async () => {
    if (!selectedFile) return;

    const formData = new FormData();
    formData.append('image', selectedFile);

    loading.classList.remove('hidden');
    result.classList.add('hidden');
    convertBtn.disabled = true;

    try {
        // --- ВОТ ТУТ МЫ ВКЛЮЧАЕМ БОНУС ---
        // Сжимаем файл перед отправкой
        const compressedBlob = await compressImage(selectedFile);
        
        const formData = new FormData();
        // Отправляем сжатый блоб вместо оригинального файла
        formData.append('image', compressedBlob, 'image.jpg'); 
        // --------------------------------
        // Внутри convertBtn.addEventListener
        const response = await fetch('/convert', {
        method: 'POST',
        body: formData
    });

    // Проверка на статус ответа (404, 500, 429 и т.д.)
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `Ошибка сервера: ${response.status}`);
    }

    const data = await response.json();

        if (data.success) {
            latexOutput.textContent = data.latex;
            // Don't render TikZ with MathJax - just show the code
            latexPreview.innerHTML = '<p style="color: #666;">Скопируйте TikZ код и вставьте в TeXmaker для просмотра</p>';
            result.classList.remove('hidden');
        } else {
            alert('Ошибка: ' + data.error);
        }
    } catch (error) {
        alert('Ошибка при обработке изображения: ' + error.message);
    } finally {
        loading.classList.add('hidden');
        convertBtn.disabled = false;
    }
});

// Copy button
copyBtn.addEventListener('click', () => {
    const text = latexOutput.textContent;
    navigator.clipboard.writeText(text).then(() => {
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Скопировано!';
        setTimeout(() => {
            copyBtn.textContent = originalText;
        }, 2000);
    });
});
