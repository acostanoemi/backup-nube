# backup-nube

Script de Python que respalda tus carpetas importantes a la nube con un comando, y las restaura si hace falta. Usa [rclone](https://rclone.org/) como motor (el que ya tenés configurado con tus nubes).

## Dos direcciones

- **backup**: tu máquina → la nube. Lo corrés seguido, por las dudas.
- **restaurar**: la nube → tu máquina. Lo corrés si se rompe o perdés algo.

## Seguridad

- Por defecto los dos corren en **modo prueba**: muestran qué harían sin tocar nada. Con `--aplicar` lo hacen de verdad.
- Usa `rclone copy`, que **nunca borra** en el destino: solo agrega y actualiza. Un backup no puede borrarte archivos por error.
- `restaurar --aplicar` pide confirmación, porque puede sobrescribir archivos locales.
- rclone sube solo lo que **cambió** desde la última vez (backup incremental): rápido y sin gastar datos de más.

## Qué respalda

Se configura en la lista `FUENTES` arriba del script. Por defecto:

- `~/proyectos` (todo el código)
- el vault del gestor de contraseñas (`vault.dat`, ya cifrado)

El destino es la nube `REMOTE` (por defecto `onedrive:backup-noemi`). Editá ambos a gusto.

## Requisitos

- Python 3
- rclone configurado (que `rclone listremotes` muestre tus nubes).

## Uso

```bash
python3 backup.py backup                # muestra qué subiría
python3 backup.py backup --aplicar      # sube de verdad
python3 backup.py restaurar             # muestra qué bajaría
python3 backup.py restaurar --aplicar   # baja de verdad (pide confirmación)
```

Cada corrida real deja una línea en `~/.backup_nube.log` con la fecha.

## Importante sobre el vault

El vault se respalda cifrado (seguro subirlo). Pero para abrirlo necesitás tu **master password**, que no está en ningún archivo: anotala en un lugar seguro y offline, aparte de la compu. La nube guarda el candado cerrado; la llave sigue solo con vos.

## Roadmap

- [x] v1: backup y restauración a la nube con modo prueba
- [ ] v2: correr solo (automático) cada cierto tiempo con cron
- [ ] v3: backup cifrado extra (rclone crypt) para carpetas sensibles
