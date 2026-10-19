# DVD Saito

Editor de fotos de escritorio para Windows con estética Windows 98. Filtros
retro y Y2K, ajustes de color, estirado de proporciones y sello de fecha como
el de las cámaras digitales viejas.

![tema](https://img.shields.io/badge/tema-Windows%2098-008080) ![python](https://img.shields.io/badge/python-3.13-blue)

## Descarga

El ejecutable listo para usar está en [Releases](https://github.com/maaurissio/dvdsaito/releases).
Se descarga `DVD Saito.exe`, doble clic y listo: no requiere instalación.

## Qué hace

- **46 filtros en 6 categorías**: Digicam (CCD, Webcam, Nokia, CCTV...),
  Analógico (Polaroid, Huji 98, Kodak Gold...), Artístico (Sketch, Comic,
  Ojo de Pez...), Lo-Fi (Pixelado, Game Boy, Deep Fry...), VHS/TV (VHS, CRT,
  Glitch...) y Estético (Bleach Bypass, Vaporwave, Teal & Orange...).
- **Miniaturas en vivo**: cada botón de filtro muestra tu foto con ese efecto.
- **Ajustes de color**: brillo, contraste, saturación, temperatura, tinte,
  luces, sombras y nitidez.
- **Textura**: grano, viñeta y desvanecido.
- **Lo-Fi**: baja resolución, compresión JPEG real y fuga de luz, aplicables
  sobre cualquier filtro.
- **Sello de fecha**: dígitos de siete segmentos en ámbar, con cinco formatos
  (incluido el japonés `'94年 1月21日`). La fecha se toma de los metadatos
  EXIF de la foto, o de la fecha del archivo, y también se puede escribir a mano.
- **Proporciones / estirado**: deformar la imagen a 1:1, 4:3, 16:9, 9:16, con
  sliders de ancho y alto, o escribiendo el tamaño exacto en píxeles.
- **Videos**: abre mp4, mov, avi, mkv, webm... y aplica los mismos filtros,
  ajustes y estirado que a las imágenes. Al guardar se exporta un mp4 con el
  audio original (el botón "Aplicar efecto" solo funciona con imágenes).
- **Efectos encadenados**: el botón "Aplicar efecto" fija el efecto actual y
  deja poner otro encima, con deshacer.
- **Arrastrar y soltar** imágenes para abrirlas.
- Al iniciar, una pantalla azul estilo Windows NT lista los archivos del
  código como si fueran drivers.

## Correr desde el código

Requiere Python 3.13 con `pillow`, `numpy`, `imageio-ffmpeg` y `tkinterdnd2`:

```
pip install pillow numpy imageio-ffmpeg tkinterdnd2
python main.py
```

## Compilar el ejecutable

Con `pyinstaller` instalado, ejecutar `reconstruir.bat`. Genera `DVD Saito.exe`
con el icono y los recursos incluidos.

## Estructura

```
main.py              punto de entrada
saito/
  app.py             ventana principal
  window.py          mover, redimensionar, minimizar y maximizar
  splash.py          pantalla de arranque azul
  dialogs.py         diálogo Acerca de
  video.py           lectura y exportación de video
  theme.py           colores, fuentes y recursos
  assets/            icono de la app
  engine/            motor de imagen
    pipeline.py      orquesta el procesamiento
    filters.py       filtros y categorías
    effects.py       pixelado, JPEG, halftone, sello de fecha
    adjustments.py   ajustes de color
    helpers.py       operaciones básicas
```

---

made by @descansandoo
