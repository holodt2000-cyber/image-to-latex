# Image to TikZ Converter

Веб-приложение для конвертации изображений в TikZ код с помощью vision-language моделей через Hugging Face Inference API.

## Возможности

- Загрузка изображений (drag & drop, выбор файла, вставка из буфера Ctrl+V)
- Стриминг генерации кода в реальном времени
- Поле пожеланий для уточнения генерации (цвета, стиль, подписи)
- Исправление уже сгенерированного кода по пожеланиям
- Открытие кода в Overleaf для компиляции и просмотра PDF
- Автопродолжение при обрезке длинного кода

## Стек

- **Backend**: Flask (Python)
- **Frontend**: Tailwind CSS, Material Icons
- **AI**: Hugging Face Inference API (бесплатно)
- **Обработка изображений**: Pillow

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd image-to-latex
```

2. Установите зависимости:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

3. Настройте токен Hugging Face:
```bash
cp .env.example .env
# Отредактируйте .env — укажите свой токен
# Получить: https://huggingface.co/settings/tokens
```

4. Запустите:
```bash
python app.py
```
Или просто запустите `START.bat`.

Откройте http://localhost:5000

## Использование

1. Загрузите изображение
2. При необходимости напишите пожелания (опционально)
3. Нажмите «Конвертировать в TikZ»
4. Скопируйте код или откройте в Overleaf
5. Для доработки — напишите что исправить и нажмите «Исправить код»

## Модели

Модель указывается в `.env` через `MODEL_ID`. Рекомендуемые:

| Модель | Описание |
|--------|----------|
| `Qwen/Qwen2-VL-72B-Instruct` | Лучшее качество, сложные диаграммы |
| `meta-llama/Llama-3.2-11B-Vision-Instruct` | Быстрее, хороший баланс |
| `mistralai/Pixtral-12B-2409` | Математика и научные диаграммы |

## Форматы изображений

PNG, JPG, JPEG, GIF, BMP, WEBP

## Решение проблем

- **401 Unauthorized** — проверьте HF_TOKEN в `.env`
- **503 Service Unavailable** — модель загружается, подождите 30-60 сек
- **404 Model not found** — проверьте название модели в `.env`

## Лицензия

MIT
