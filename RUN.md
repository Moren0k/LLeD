# Ejecución y desarrollo

Guía para instalar, configurar, ejecutar, desarrollar y empaquetar LLeD.

## Requisitos

- Windows 10 u 11 con Bluetooth.
- Una tira LED Bluetooth compatible.
- Python 3.8 o superior (para el backend).
- Node.js 18 o superior (para la interfaz).
- Para el modo ritmo: la captura de audio del sistema debe estar habilitada en
  Windows (dispositivo de grabación tipo "Mezcla estéreo").

## Instalación

Desde la carpeta del proyecto:

1. Dependencias del backend:

   ```
   pip install -r requirements.txt
   ```

2. Dependencias de la interfaz:

   ```
   npm install
   ```

## Configuración

- La aplicación funciona sin configuración manual: trae incluida la configuración
  necesaria para conectarse con Spotify.
- El dispositivo LED se selecciona desde la propia aplicación (sección Ajustes),
  que lo detecta al escanear.
- Los datos del usuario (configuración, ajustes, biblioteca de colores y sesión
  de Spotify) se guardan en la carpeta de datos de la aplicación, separada del
  directorio del proyecto.
- Opcionalmente, para usar una aplicación de Spotify propia, se puede crear un
  archivo de configuración local a partir de `config.example.json`. La
  integración con Spotify utiliza OAuth PKCE, por lo que no se necesita ni se
  debe guardar ningún secreto de cliente.

## Ejecución

### Usuario final

Instalar el instalador generado (ver "Generar builds"). La aplicación arranca su
backend automáticamente; no requiere instalar Python.

### Desarrollo

Todo en un solo comando (inicia backend, interfaz y ventana de escritorio):

```
npm run dev
```

O cada parte por separado, en terminales distintas:

```
python servidor.py       # backend (servidor local)
npm run dev:front        # interfaz en modo desarrollo
npm run dev:electron     # ventana de escritorio
```

## Generar builds

- Interfaz:

  ```
  npm run build:front
  ```

- Backend como ejecutable independiente:

  ```
  npm run build:backend
  ```

- Instalador completo (interfaz, backend e instalador de escritorio):

  ```
  npm run build
  ```

En Windows, la generación del instalador necesita permiso para crear enlaces
simbólicos. Habilitar el Modo de desarrollador de Windows o ejecutar la terminal
como Administrador antes de correr el build.

El resultado es un instalador de escritorio que se distribuye a los usuarios. Al
instalar una versión nueva sobre una anterior, los datos del usuario se
conservan.

## Pruebas

Instalar las dependencias de desarrollo y ejecutar la suite:

```
pip install -r requirements-dev.txt
pytest
```

Las pruebas se ejecutan sin hardware ni conexión de red, usando una tira LED y un
cliente de Spotify simulados.

## Pasos de validación

Antes de publicar cambios, verificar que:

- La interfaz compila sin errores: `npm run build:front`.
- Las pruebas pasan: `pytest`.
- La aplicación se conecta con el backend y responde (encender/apagar la tira,
  cambiar color, iniciar sesión con Spotify, activar los visuales).

## Procedimientos de desarrollo y mantenimiento

- El backend expone un servidor WebSocket local que la interfaz consume; el
  visual remoto se publica en la red local desde el propio backend.
- El motor de visuales (`motor_visual.js`) es compartido por la interfaz y por la
  página del visual remoto: los cambios en ese archivo afectan a ambos.
- Las dependencias se gestionan en `requirements.txt` (backend) y `package.json`
  (interfaz). Mantener ambas listas al día al agregar o quitar librerías.
- No se debe versionar información sensible ni datos locales del usuario; esos
  archivos quedan fuera del control de versiones.
- Para publicar una versión nueva, regenerar el instalador y distribuirlo.
