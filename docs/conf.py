import os
import sys

sys.path.insert(0, os.path.abspath("../"))

project = "EscortDollars Backend"
copyright = "2024"
author = "Votre équipe"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "alabaster"
