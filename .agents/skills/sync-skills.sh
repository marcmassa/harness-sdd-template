#!/bin/bash

# Script para descargar skills desde el Registry Centralizado

REGISTRY_URL="https://gitlab.devops.onesait.com/onesait/technology/devops/infrastructure/agent-skills-registry.git"
SKILLS_DIR=".agents/skills"
TEMP_DIR=".agents/.tmp_skills"

echo "Updating skills from registry..."

# Crear directorio si no existe
mkdir -p "$SKILLS_DIR"

# Clonar registry en directorio temporal
rm -rf "$TEMP_DIR"
git clone --depth 1 "$REGISTRY_URL" "$TEMP_DIR" --quiet

if [ $? -eq 0 ]; then
    # Copiar skills (sin sobreescribir el README.md principal de .agents/skills)
    cp -r "$TEMP_DIR/skills/"* "$SKILLS_DIR/"
    echo "Skills updated successfully."
else
    echo "Error: Could not update skills from registry."
    exit 1
fi

# Limpieza
rm -rf "$TEMP_DIR"
