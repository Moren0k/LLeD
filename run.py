#!/usr/bin/env python3
"""Launcher - Configura automáticamente y lanza servidor."""

import subprocess
import sys
import importlib

deps_required = {
    "scipy": "scipy>=1.11.0",
    "joblib": "joblib>=1.3.0",
    "sklearn": "scikit-learn>=1.3.0",
}

print("═" * 70)
print("🎵 SISTEMA DE SINCRONIZACIÓN LED - VERSIÓN FINAL")
print("═" * 70)

# Verifica dependencias
print("\n📦 Verificando dependencias...")
missing = []
for module, package in deps_required.items():
    try:
        importlib.import_module(module)
        print(f"  ✅ {package}")
    except ImportError:
        print(f"  ⏳ Instalando {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", package])
        print(f"  ✅ {package}")

print("\n" + "═" * 70)
print("✅ Sistema listo para ejecutar\n")

# Inicia servidor
print("🚀 Iniciando servidor...\n")
subprocess.call([sys.executable, "servidor.py"])
