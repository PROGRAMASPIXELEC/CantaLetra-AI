# CantaLetra AI

Aplicación web MVP para cargar canciones, editar letras y separar voz/instrumental con Demucs.

## Ejecutar localmente
Requisitos: Python 3.10+ y FFmpeg.

```bash
cd backend
python -m venv .venv
pip install -r requirements.txt
uvicorn main:app --reload
```
Abre http://127.0.0.1:8000

## Despliegue
Conecta el repositorio a Render usando New → Blueprint; Render detectará `render.yaml`.

## Estado
- Carga y reproducción: implementada.
- Edición y guardado de letras: implementada.
- Separación de pistas: disponible si Demucs y FFmpeg están instalados.
- Nueva interpretación cantada: pendiente de integrar un motor especializado de singing voice conversion con alineación de melodía y tiempos. No se simula una generación que no existe.

El uso de una voz identificable requiere autorización del titular y los derechos necesarios sobre grabación y composición. Antes de producción configura autenticación, almacenamiento persistente privado, borrado automático y límites de uso.
