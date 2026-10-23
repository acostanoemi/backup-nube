#!/usr/bin/env python3
"""
Backup y restauracion a la nube (rclone) - v3

Respalda tus carpetas importantes a la nube con un comando, y las restaura
si hace falta. Usa rclone (que ya tenés configurado con tus nubes).

Direcciones:
  backup    : tu maquina  -> la nube   (modo prueba por defecto, --aplicar para hacerlo)
  restaurar : la nube      -> tu maquina
  auto      : backup directo sin preguntar (para cron)

VERSIONADO (lo importante de esta version): cuando un archivo cambia, la
version vieja NO se pisa: se guarda en una carpeta con fecha en la nube
(_versiones/FECHA). Asi, si un archivo se corrompe o lo editás mal y despues
corre el backup, podés recuperar la version anterior. Un backup que solo
pisa puede arruinarse copiando un desastre; con versionado, no.

Usa 'rclone copy', que nunca borra en el destino: solo agrega y actualiza.

Uso:
    python3 backup.py backup                # muestra que subiria
    python3 backup.py backup --aplicar      # sube de verdad
    python3 backup.py restaurar             # muestra que bajaria
    python3 backup.py restaurar --aplicar   # baja de verdad (pide confirmacion)
    python3 backup.py auto                  # backup directo (para cron)
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
EXCLUIR = [
    ".git/**", "__pycache__/**", "*.pyc", "*.pcap",
    "grafico_*.png", "*.log", "venv/**", ".venv/**",
]
# -----------------------------------

ARCHIVO_LOG = HOME / ".backup_nube.log"


def existe_rclone():
    try:
        subprocess.run(["rclone", "version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


def construir_comando(origen, destino, es_archivo, aplicar, dir_versiones=None):
    """
    Arma el comando rclone.
      - 'copyto' para un archivo suelto, 'copy' para carpetas.
      - -v para que loguee cada archivo (asi contamos el resumen).
      - --backup-dir: a donde van las versiones viejas (solo carpetas, en backup).
      - --dry-run en modo prueba.
    """
    verbo = "copyto" if es_archivo else "copy"
    cmd = ["rclone", verbo, str(origen), str(destino), "-v"]
    if not es_archivo:
        for patron in EXCLUIR:
            cmd += ["--exclude", patron]
        if dir_versiones:
            cmd += ["--backup-dir", dir_versiones]
    if not aplicar:
        cmd.append("--dry-run")
    return cmd


def registrar(texto):
    marca = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{marca}] {texto}\n")


def contar_en_salida(texto):
    """Cuenta en la salida de rclone cuantos archivos se copiaron/versionaron."""
    nuevos = texto.count("Copied (new)")
    reemplazados = texto.count("Copied (replaced existing)")
    # Los archivos movidos a _versiones aparecen como "Moved"
    versionados = texto.count("Moved (")
    return nuevos, reemplazados, versionados


def correr(direccion, aplicar):
    if not existe_rclone():
        print("No encontré rclone. Instalalo o revisá que esté en el PATH.")
        return

    modo = "APLICANDO" if aplicar else "PRUEBA (no toca nada)"
    fecha = time.strftime("%Y-%m-%d_%H-%M")
    dir_versiones = f"{REMOTE}/_versiones/{fecha}"

    print(f"=== {direccion.upper()}  |  Modo: {modo} ===")
    print(f"Nube: {REMOTE}")
    if direccion == "backup":
        print(f"Versiones viejas van a: {REMOTE}/_versiones/{fecha}")
    print()

    tot_nuevos = tot_reempl = tot_version = 0
    errores = 0

    for ruta_local, subcarpeta, es_archivo in FUENTES:
        destino_nube = f"{REMOTE}/{subcarpeta}"

        if direccion == "backup":
            origen, destino = ruta_local, destino_nube
            if not ruta_local.exists():
                print(f"[saltado] no existe: {ruta_local}")
                continue
            dv = None if es_archivo else dir_versiones
        else:  # restaurar
            origen, destino = destino_nube, ruta_local
            dv = None

        print(f"-> {origen}\n   {destino}")
        cmd = construir_comando(origen, destino, es_archivo, aplicar, dv)
        # Capturamos la salida para armar el resumen (y la mostramos igual)
        res = subprocess.run(cmd, capture_output=True, text=True)
        salida = res.stdout + res.stderr
        n, r, v = contar_en_salida(salida)
        tot_nuevos += n
        tot_reempl += r
        tot_version += v
        if res.returncode != 0:
            errores += 1
            print("   (hubo un problema; revisá el log)")
            registrar(f"ERROR en {direccion} de {origen}: {salida.strip()[-200:]}")
        print(f"   nuevos: {n}  reemplazados: {r}  versionados: {v}\n")

    # Resumen final
    print("-" * 40)
    verbo = "se subirian" if not aplicar else "subidos"
    print(f"RESUMEN: {tot_nuevos} nuevo(s), {tot_reempl} actualizado(s) {verbo}, "
          f"{tot_version} version(es) vieja(s) guardada(s).")
    if errores:
        print(f"⚠ {errores} fuente(s) con problemas. Mirá {ARCHIVO_LOG}")
    if not aplicar:
        print("(Modo prueba: no se tocó nada. Usá --aplicar para hacerlo.)")

    if aplicar:
        registrar(f"{direccion} ok - nuevos:{tot_nuevos} actualizados:{tot_reempl} "
                  f"versionados:{tot_version} errores:{errores}")


def main():
    p = argparse.ArgumentParser(description="Backup y restauracion a la nube con rclone.")
    p.add_argument("direccion", choices=["backup", "restaurar", "auto"],
                   help="backup = subir; restaurar = bajar; auto = backup directo (cron)")
    p.add_argument("-a", "--aplicar", action="store_true",
                   help="hacerlo de verdad (sin esto, solo muestra que haria)")
    args = p.parse_args()

    if args.direccion == "auto":
        print(f"\n===== Corrida automatica: {time.strftime('%Y-%m-%d %H:%M:%S')} =====")
        correr("backup", aplicar=True)
        return

    if args.direccion == "restaurar" and args.aplicar:
        r = input("Restaurar va a traer archivos de la nube y puede sobrescribir "
                  "los locales. ¿Seguro? (si/no): ").strip().lower()
        if r != "si":
            print("Cancelado.")
            return

    correr(args.direccion, args.aplicar)


if __name__ == "__main__":
    main()
