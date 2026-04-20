# Image to TikZ Converter

Веб-приложение для конвертации изображений в TikZ код для использования в LaTeX/TeXmaker.

## Возможности

- Загрузка изображений через drag & drop или выбор файла
- Вставка изображений из буфера обмена (Ctrl+V)
- Генерация базового TikZ шаблона
- Копирование TikZ кода в буфер обмена

## Технологии

- **Backend**: Flask (Python)
- **Frontend**: HTML, CSS, JavaScript
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
4. Скопируйте сгенерированный TikZ код
5. Вставьте код в TeXmaker

## Улучшенная векторизация

Для лучшей векторизации изображений рекомендуется использовать:

### Вариант 1: Inkscape (рекомендуется)
1. Установите [Inkscape](https://inkscape.org/)
2. Откройте изображение в Inkscape
3. Используйте Path → Trace Bitmap для векторизации
4. Экспортируйте как TikZ через расширение

### Вариант 2: Potrace
1. Установите [Potrace](http://potrace.sourceforge.net/)
2. Конвертируйте изображение в SVG: `potrace image.pbm -s -o output.svg`
3. Используйте svg2tikz для конвертации SVG в TikZ

## Поддерживаемые форматы

- PNG
- JPG/JPEG
- GIF
- BMP

## Лицензия

MIT
