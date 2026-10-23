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

## Automático con cron

El comando `auto` hace el backup directo, sin preguntar ni modo prueba. Está pensado para que cron (el programador de tareas de Linux) lo corra solo.

Para programarlo, editá tu crontab:

```bash
crontab -e
```

Y agregá una línea (backup todos los días a las 21:00):

```
0 21 * * *  cd /home/noemi/proyectos/backup-nube && /usr/bin/python3 backup.py auto >> /home/noemi/.backup_nube.log 2>&1
```

Los 5 campos son: minuto, hora, día del mes, mes, día de semana. `0 21 * * *` = a las 21:00 todos los días. La salida se guarda en el log para revisarla después.

**Nota en laptops:** si la compu está apagada o suspendida a esa hora, cron no corre. Para que el backup se haga igual cuando prendas, se usa `anacron` (ver más abajo).

### Que no se pierda un backup si la compu estuvo apagada (anacron)

cron solo corre si la compu está prendida a la hora programada. En una laptop, eso se escapa seguido. `anacron` lo resuelve: al prender la compu, corre el backup que se haya saltado.

Configuración a nivel usuario (no necesita root):

```bash
mkdir -p ~/.anacron/spool ~/.anacron/etc
nano ~/.anacron/etc/anacrontab
```

Contenido del `anacrontab` (período en días, retraso en minutos, id, comando):

```
1  5  backup.diario  cd /home/noemi/proyectos/backup-nube && /usr/bin/python3 backup.py auto >> /home/noemi/.backup_nube.log 2>&1
```

Y que anacron se dispare al arrancar, agregando al crontab (`crontab -e`):

```
@reboot  /usr/sbin/anacron -s -t /home/noemi/.anacron/etc/anacrontab -S /home/noemi/.anacron/spool
```

Así quedan dos capas: cron a las 21:00 (si está prendida) + anacron al prender (si se saltó un día).

Probar anacron sin reiniciar:

```bash
/usr/sbin/anacron -f -n -t ~/.anacron/etc/anacrontab -S ~/.anacron/spool
```

## Versionado

Cuando un archivo cambia, su versión vieja no se pisa: se guarda en `_versiones/FECHA/` en la nube (vía `rclone --backup-dir`). Si un archivo se corrompe o lo editás mal y después corre el backup, podés recuperar la versión anterior. Protege contra el error clásico: que el backup copie un desastre y arruine la copia buena.

## Requisitos de ruta

cron no sabe en qué carpeta estás, por eso la línea hace `cd` a la carpeta del script primero y usa la ruta completa de python (`/usr/bin/python3`).

## Roadmap

- [x] v1: backup y restauración a la nube con modo prueba
- [x] v2: comando `auto` para correr solo con cron
- [x] v3: versionado (`--backup-dir`), resumen al final y anacron para laptops
- [ ] v4: backup cifrado extra (rclone crypt) para carpetas sensibles
- [ ] v5: limpiar versiones viejas automáticamente (retención)
