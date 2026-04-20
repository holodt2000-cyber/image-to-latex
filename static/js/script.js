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
        const response = await fetch('/convert', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            latexOutput.textContent = data.latex;
            latexPreview.innerHTML = `\\[${data.latex}\\]`;

            // Render MathJax
            if (window.MathJax) {
                MathJax.typesetPromise([latexPreview]);
            }

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
