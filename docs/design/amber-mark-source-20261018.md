# Происхождение янтарного знака MAMA Helper

Дата: 18 октября 2026 года.

## Исходники и файлы

- Выбранный референс, третий концепт: `C:/Users/Admin/Documents/Codex/2026-10-17/codex-mcp-add-motionsites-npx-y/outputs/mama-concept-3-olive-evening.png`.
- Оригинальный результат встроенного `image_gen__imagegen`: `C:/Users/Admin/.codex/generated_images/01a14bee-54c2-7bb1-be5d-e339c1e2e6d1/exec-8314001c-6568-42e1-807e-4911b369ee9e.png`, PNG 1254×1254 с прозрачностью.
- Целевой растровый ассет для интерфейса: `C:/Users/Admin/Documents/ChatGPT/MAMA help/app/public/media/room/amber-leaf.png`, PNG 512×512, RGBA. Уменьшен из оригинала с сохранением alpha-канала методом HighQualityBicubic в System.Drawing; исходный файл генерации сохранён.
- Отдельный векторный файл формы: `C:/Users/Admin/Documents/ChatGPT/MAMA help/app/public/media/room/amber-leaf.svg`, автоматическая трассировка целевого PNG, без встроенного PNG и внешних изображений.

Заданное прочтение знака — две абстрактные обнимающие формы: большая внешняя напоминает маму, меньшая внутренняя — ребёнка. Это заданная ассоциация, а не результат независимого пользовательского исследования.

## Точный использованный промпт

Параметры вызова: `referenced_image_paths` — путь третьего концепта выше; `transparent_background: true`. Использован встроенный imagegen, без CLI/API fallback.

```text
Use case: background-extraction. Asset type: one isolated raster brand mark for MAMA helper, used at 32px CSS size. Input image 1 is the edit target and style reference. Extract and carefully reconstruct ONLY the small golden amber emblem at the TOP LEFT of the reference, immediately to the left of the Russian app title. Preserve its exact distinctive abstract silhouette: two gently curved embracing leaf-like forms, the larger outer upward sweeping form suggesting a mother holding the smaller inner form suggesting a child. This poetic mother-and-child shape is essential. Keep it abstract, with no people, faces, eyes, hands, or literal anatomy. Do not turn it into a botanical sprig or a collection of many leaves. Preserve the elegant narrow pointed ends, warm golden amber color, and subtle realistic frosted amber glass material with delicate dimensional highlights, very close to the reference. One symbol only, centered, upright, filling about 80 percent of a square canvas, readable at 32px. Output a truly transparent PNG with clean antialiased alpha around the silhouette; no colored backdrop, no circle, no badge, no plate, no ground shadow, no glow halo, no UI, no text, no watermark. Desired final asset 512x512 pixels. Match the original top-left emblem, not the circular avatar lower on the page.
```

## Автоматическая трассировка SVG

Использован [официальный пакет VTracer 0.6.15 из PyPI](https://pypi.org/project/vtracer/0.6.15/), лицензия инструмента MIT. Это лицензия трассировщика, а не юридическое заключение о правах на знак.

Временный вход для трассировки получен из целевого PNG: RGB сохранён, alpha ≥128 преобразован в 255, alpha <128 — в 0. Сам PNG для интерфейса не изменялся. Это позволяет трассировать видимый силуэт без слабых полупрозрачных артефактов вокруг него. Контуры получены алгоритмом, вручную не рисовались; новый знак не генерировался.

```python
vtracer.convert_image_to_svg_py(
    input_png, output_svg,
    colormode='color', hierarchical='stacked', mode='spline',
    filter_speckle=0, color_precision=8, layer_difference=4,
    corner_threshold=60, length_threshold=3.5,
    max_iterations=10, splice_threshold=45, path_precision=4,
)
```

К SVG добавлен `viewBox="0 0 512 512"`; данные контуров после трассировки не менялись. Файл содержит 15069 элементов `path`, 0 элементов `image`, 0 атрибутов `href`. Размер — 1711165 байт. Это технический векторный мастер после автотрассировки, требующий отдельной ручной оптимизации для компактного фирменного набора. В интерфейсе предназначен для использования PNG; подключение SVG кодом не выполнялось.

## Проверка и ограничения

PNG просмотрен визуально; технически подтверждены размеры 512×512 и настоящий alpha-канал. SVG отрендерен через bundled sharp/librsvg и визуально сопоставлен с PNG на светлом и тёмном фоне в размере 300 px и 32 px. Две основные формы сохраняются. Пересечение бинарных силуэтов PNG и SVG при пороге alpha 128, делённое на объединение, — 0.9776799247. Это техническая метрика, а не оценка узнаваемости.

PNG является растровым изображением и сам по себе не является готовым вектором. Отдельный SVG содержит настоящие контуры, но автотрассировка аппроксимирует стеклянные переходы цветными областями и не сохраняет всю исходную полупрозрачность. Полный фирменный комплект, ручная доводка геометрии, полная проверка малых размеров и независимое исследование ассоциаций не выполнялись.

Полноформатная юридическая проверка, поиск сходства и проверка товарного знака не выполнялись. Новая генерация не гарантирует уникальности во всём мире, исключительных прав или возможности регистрации. В этой работе отдельные стоковые значки, чужие логотипы, шрифты и водяные знаки не использовались; происхождение выбранного концепта за пределами указанного файла повторно не проверялось.

## SHA256

| Файл | SHA256 |
|---|---|
| Выбранный третий концепт | `FABB56F4F504E936AE4303615CA40E35001091CDD312F81068480774783EE5DC` |
| Оригинальный PNG генерации | `1A6FC4C48E044266DB135684613661A32A6551D381EDEA696BF17D48E5AEC471` |
| Целевой `amber-leaf.png` | `3FE4E1AD498B1BBBE6A1F070DD0F6511080FB0552BCC0D55F2A82DB2A0CDF709` |
| Трассированный `amber-leaf.svg` | `DC0FFA4721B1E080B61D823E83E90095B5704CEF5E27A8E8B7EE646A103D862C` |
