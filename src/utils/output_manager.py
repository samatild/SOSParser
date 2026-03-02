#!/usr/bin/env python3
"""Output directory management utilities"""

import shutil
from pathlib import Path
from utils.logger import Logger


def setup_output_directory(output_dir: Path, template_dir: Path, static_dir: Path):
    """
    Set up the output directory structure and copy static assets.
    
    Args:
        output_dir: Directory where report will be generated
        template_dir: Directory containing templates (with styles/ and scripts/)
        static_dir: Directory containing static assets (images/)
    """
    Logger.debug(f"Setting up output directory: {output_dir}")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories
    styles_dir = output_dir / 'styles'
    scripts_dir = output_dir / 'scripts'
    images_dir = output_dir / 'images'
    
    styles_dir.mkdir(exist_ok=True)
    scripts_dir.mkdir(exist_ok=True)
    images_dir.mkdir(exist_ok=True)
    
    # Copy styles
    src_styles = template_dir / 'styles'
    if src_styles.exists():
        for style_file in src_styles.glob('*.css'):
            try:
                shutil.copy2(style_file, styles_dir / style_file.name)
                Logger.debug(f"Copied style: {style_file.name}")
            except Exception as e:
                Logger.warning(f"Failed to copy {style_file.name}: {e}")
    else:
        Logger.warning(f"Styles directory not found: {src_styles}")
    
    # Copy scripts
    src_scripts = template_dir / 'scripts'
    if src_scripts.exists():
        for script_file in src_scripts.glob('*.js'):
            try:
                shutil.copy2(script_file, scripts_dir / script_file.name)
                Logger.debug(f"Copied script: {script_file.name}")
            except Exception as e:
                Logger.warning(f"Failed to copy {script_file.name}: {e}")
    else:
        Logger.warning(f"Scripts directory not found: {src_scripts}")
    
    # Copy images from template directory (logos, etc.)
    src_images_template = template_dir / 'images'
    if src_images_template.exists():
        for image_file in src_images_template.iterdir():
            if image_file.is_file():
                try:
                    shutil.copy2(image_file, images_dir / image_file.name)
                    Logger.debug(f"Copied image from templates: {image_file.name}")
                except Exception as e:
                    Logger.warning(f"Failed to copy {image_file.name}: {e}")
    
    # Copy images from static directory (if exists)
    src_images = static_dir / 'images'
    if src_images.exists():
        for image_file in src_images.iterdir():
            if image_file.is_file():
                try:
                    shutil.copy2(image_file, images_dir / image_file.name)
                    Logger.debug(f"Copied image from static: {image_file.name}")
                except Exception as e:
                    Logger.warning(f"Failed to copy {image_file.name}: {e}")
    
    Logger.debug("Output directory setup complete")
