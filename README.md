# Image to TikZ Converter

Веб-приложение для конвертации изображений в TikZ код с использованием AI моделей от Hugging Face.

## Возможности

- Загрузка изображений через drag & drop или выбор файла
- Вставка изображений из буфера обмена (Ctrl+V)
- AI-генерация TikZ кода с помощью vision-language моделей
- Копирование TikZ кода в буфер обмена
- Поддержка различных моделей для оптимального качества

## Технологии

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **AI**: Hugging Face Inference API
- **Image Processing**: Pillow

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd image-to-latex
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте Hugging Face токен:
```bash
# Скопируйте пример конфигурации
cp .env.example .env

# Получите токен на https://huggingface.co/settings/tokens
# Отредактируйте .env и добавьте ваш токен:
HF_TOKEN=hf_ваш_токен_здесь
```

## Запуск

Просто запустите `START.bat` или:

```bash
python app.py
```

Откройте браузер и перейдите по адресу: http://localhost:5000

## Использование

1. Откройте веб-интерфейс
2. Загрузите изображение (или вставьте через Ctrl+V)
3. Нажмите "Конвертировать в TikZ"
4. Дождитесь обработки (30-60 секунд при первом запуске модели)
5. Скопируйте сгенерированный TikZ код
6. Вставьте код в TeXmaker или Overleaf

## Рекомендуемые модели

В файле `.env` вы можете выбрать модель:

### 1. Qwen/Qwen2-VL-72B-Instruct (по умолчанию)
- Лучшее качество для сложных диаграмм
- Отличное понимание математических формул
- Время обработки: ~30-60 сек

### 2. meta-llama/Llama-3.2-11B-Vision-Instruct
- Хороший баланс скорости и качества
- Быстрее чем Qwen
- Время обработки: ~20-40 сек

### 3. mistralai/Pixtral-12B-2409
- Специализация на математике и научных диаграммах
- Отличная точность для формул
- Время обработки: ~25-45 сек

Чтобы изменить модель, отредактируйте `.env`:
```bash
MODEL_ID=meta-llama/Llama-3.2-11B-Vision-Instruct
```

## Поддерживаемые форматы

- PNG
- JPG/JPEG
- GIF
- BMP
- WEBP

## Устранение неполадок

### Ошибка "401 Unauthorized"
- Проверьте, что HF_TOKEN правильно указан в `.env`
- Убедитесь, что токен активен на https://huggingface.co/settings/tokens

### Ошибка "503 Service Unavailable"
- Модель загружается в первый раз (подождите 30-60 секунд)
- Попробуйте другую модель

### Ошибка "404 Model not found"
- Проверьте правильность названия модели в `.env`
- Убедитесь, что модель доступна на Hugging Face

## Лицензия

MIT
