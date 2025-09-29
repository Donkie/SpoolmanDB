#!/bin/bash
set -e

echo "===== Création d'un environnement virtuel Python ====="
python3 -m venv venv
source venv/bin/activate

echo "===== Mise à jour de pip ====="
pip install --upgrade pip

echo "===== Installation de check-jsonschema ====="
pip install check-jsonschema

echo "===== Validation de materials.json ====="
check-jsonschema --schemafile materials.schema.json materials.json

echo "===== Validation de tous les fichiers dans filaments/ ====="
check-jsonschema --schemafile filaments.schema.json filaments/*

echo "===== Compilation des filaments ====="
python3 scripts/compile_filaments.py

echo "===== Vérification terminée ====="
echo "Tous les checks passent localement ! ✅"

