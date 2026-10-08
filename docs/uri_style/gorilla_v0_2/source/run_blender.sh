#!/usr/bin/env bash
set -euo pipefail
export LD_LIBRARY_PATH=/home/ethan/Softwares/blender-local/root/usr/lib:/home/ethan/Softwares/blender-local/root/usr/lib/aarch64-linux-gnu:/home/ethan/Softwares/blender-local/root/usr/lib/aarch64-linux-gnu/lapack:/home/ethan/Softwares/blender-local/root/usr/lib/aarch64-linux-gnu/blas
export BLENDER_SYSTEM_SCRIPTS=/home/ethan/Softwares/blender-local/root/usr/share/blender/scripts
export BLENDER_SYSTEM_DATAFILES=/home/ethan/Softwares/blender-local/root/usr/share/blender/datafiles
export PYTHONHOME=/usr
export PYTHONNOUSERSITE=1
exec /home/ethan/Softwares/blender-local/root/usr/bin/blender --background --factory-startup --threads 6 "$@"
