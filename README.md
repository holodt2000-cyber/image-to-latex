# Image to LaTeX Converter

Веб-приложение для конвертации изображений математических формул в LaTeX код.

## Возможности

- Загрузка изображений через drag & drop или выбор файла
- Автоматическое распознавание математических формул
- Конвертация в LaTeX код
- Предпросмотр результата с рендерингом формулы
- Копирование LaTeX кода в буфер обмена

## Технологии

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
- **OCR**: pix2tex (LaTeX OCR)
- **Рендеринг**: MathJax

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

## Запуск

```bash
python app.py
```

Откройте браузер и перейдите по адресу: http://localhost:5000

## Использование

1. Откройте веб-интерфейс
2. Загрузите изображение с математической формулой
3. Нажмите "Конвертировать в LaTeX"
4. Получите LaTeX код и предпросмотр формулы
5. Скопируйте код для использования

## Поддерживаемые форматы

- PNG
- JPG/JPEG
- GIF
- BMP

## Лицензия

MIT
