#!/usr/bin/env python3
"""
Backup y restauracion a la nube (rclone) - v1

Respalda tus carpetas importantes a la nube con un comando, y las restaura
si hace falta. Usa rclone (que ya tenés configurado con tus nubes).

Dos direcciones:
  backup    : tu maquina  -> la nube   (lo corrés seguido, por las dudas)
  restaurar : la nube      -> tu maquina (lo corrés si se rompe/perdés algo)

Por defecto los dos corren en modo PRUEBA (--dry-run de rclone): te muestran
que harian sin tocar nada. Con --aplicar lo hacen de verdad.

Usa 'rclone copy', que NUNCA borra en el destino: solo agrega y actualiza.
Asi un backup no puede borrarte nada por error.

Requisitos: rclone configurado (rclone listremotes debe mostrar tus nubes).

Uso:
    python3 backup.py backup                # muestra que subiria
    python3 backup.py backup --aplicar      # sube de verdad
    python3 backup.py restaurar             # muestra que bajaria
    python3 backup.py restaurar --aplicar   # baja de verdad
"""

import sys
import time
import argparse
import subprocess
from pathlib import Path

# --- Config: editá esto a gusto ---
REMOTE = "onedrive:backup-noemi"      # nube destino y carpeta base

# Que respaldar: (ruta local, subcarpeta en la nube, es_archivo_suelto)
HOME = Path.home()
FUENTES = [
    (HOME / "proyectos", "proyectos", False),
    (HOME / "proyectos/gestor-contraseñas/vault.dat", "gestor/vault.dat", True),
]

# Que NO subir (ruido que no vale la pena respaldar).
# El codigo ya vive en GitHub; el .git es enorme y lento de sincronizar.
EXCLUIR = [
    ".git/**",            # base interna de git (miles de archivitos)
    "__pycache__/**",     # cache de python
    "*.pyc",
    "*.pcap",             # capturas del sniffer
    "grafico_*.png",      # graficos generados
    "*.log",
    "venv/**", ".venv/**",
]
# -----------------------------------

ARCHIVO_LOG = HOME / ".backup_nube.log"


def existe_rclone():
    try:
        subprocess.run(["rclone", "version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def construir_comando(origen, destino, es_archivo, aplicar):
    """
    Arma el comando rclone. 'copy' para carpetas, 'copyto' para un archivo suelto.
    --dry-run si no se aplica (modo prueba).
    """
    verbo = "copyto" if es_archivo else "copy"
    cmd = ["rclone", verbo, str(origen), str(destino), "-P"]
    # Las exclusiones solo aplican a carpetas (copy), no a un archivo suelto (copyto)
    if not es_archivo:
        for patron in EXCLUIR:
            cmd += ["--exclude", patron]
    if not aplicar:
        cmd.append("--dry-run")
    return cmd


def registrar(texto):
    """Agrega una linea con fecha al log."""
    marca = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{marca}] {texto}\n")


def correr(direccion, aplicar):
    if not existe_rclone():
        print("No encontré rclone. Instalalo o revisá que esté en el PATH.")
        return

    modo = "APLICANDO" if aplicar else "PRUEBA (no toca nada)"
    print(f"=== {direccion.upper()}  |  Modo: {modo} ===")
    print(f"Nube: {REMOTE}\n")

    errores = 0
    for ruta_local, subcarpeta, es_archivo in FUENTES:
        destino_nube = f"{REMOTE}/{subcarpeta}"

        if direccion == "backup":
            origen, destino = ruta_local, destino_nube
            # Para backup chequeamos que exista lo local
            if not ruta_local.exists():
                print(f"[saltado] no existe: {ruta_local}")
                continue
        else:  # restaurar: la nube es el origen
            origen, destino = destino_nube, ruta_local

        print(f"-> {origen}")
        print(f"   {destino}")
        cmd = construir_comando(origen, destino, es_archivo, aplicar)
        resultado = subprocess.run(cmd)
        if resultado.returncode != 0:
            errores += 1
            print("   (hubo un problema con este)")
        print()

    if aplicar:
        registrar(f"{direccion} - {'con errores' if errores else 'ok'}")
    if errores:
        print(f"Terminó con {errores} problema(s). Revisá los mensajes de arriba.")
    elif aplicar:
        print("Listo.")
    else:
        print("Eso es lo que haria. Corré con --aplicar para hacerlo de verdad.")


def main():
    p = argparse.ArgumentParser(description="Backup y restauracion a la nube con rclone.")
    p.add_argument("direccion", choices=["backup", "restaurar", "auto"],
                   help="backup = subir; restaurar = bajar; "
                        "auto = backup directo sin preguntar (para cron)")
    p.add_argument("-a", "--aplicar", action="store_true",
                   help="hacerlo de verdad (sin esto, solo muestra que haria)")
    args = p.parse_args()

    # 'auto': backup de verdad, sin preguntas ni modo prueba. Pensado para cron.
    if args.direccion == "auto":
        print(f"\n===== Corrida automatica: {time.strftime('%Y-%m-%d %H:%M:%S')} =====")
        correr("backup", aplicar=True)
        return

    # La restauracion sobrescribe archivos locales: avisamos
    if args.direccion == "restaurar" and args.aplicar:
        r = input("Restaurar va a traer archivos de la nube y puede sobrescribir "
                  "los locales. ¿Seguro? (si/no): ").strip().lower()
        if r != "si":
            print("Cancelado.")
            return

    correr(args.direccion, args.aplicar)


if __name__ == "__main__":
    main()
