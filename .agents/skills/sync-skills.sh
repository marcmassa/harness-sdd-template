#!/bin/bash

# Script to download skills from the central Registry

REGISTRY_URL="https://gitlab.devops.onesait.com/onesait/technology/devops/infrastructure/agent-skills-registry.git"
SKILLS_DIR=".agents/skills"
TEMP_DIR=".agents/.tmp_skills"

echo "Updating skills from registry..."

mkdir -p "$SKILLS_DIR"

rm -rf "$TEMP_DIR"
git clone --depth 1 "$REGISTRY_URL" "$TEMP_DIR" --quiet

if [ $? -eq 0 ]; then
    # Clean current skills (keeping README.md and sync-skills.sh)
    find "$SKILLS_DIR" -mindepth 1 -maxdepth 1 ! -name 'README.md' ! -name 'sync-skills.sh' -exec rm -rf {} +
    
    # Copy new skills
    cp -r "$TEMP_DIR/skills/"* "$SKILLS_DIR/"
    echo "Skills updated successfully."
else
    echo "Error: Could not update skills from registry."
    exit 1
fi

rm -rf "$TEMP_DIR"
