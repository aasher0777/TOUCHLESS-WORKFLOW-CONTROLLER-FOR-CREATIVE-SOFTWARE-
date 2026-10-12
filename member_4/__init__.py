"""
Member 4: OS Context & Automation Specialist (Swastik)
-----------------------------------------------------
- Develops the context routing queries using pygetwindow to identify if software like Adobe Premiere Pro or Figma is actively running.
- Matches the classified state from Member 3 with the specific application's gesture dictionary.
- Integrates pyautogui and keyboard libraries to successfully execute the resulting system-level macros directly into the operating system.
"""

from .member_4 import OSMacroController, MacroAction

__all__ = ["OSMacroController", "MacroAction"]
