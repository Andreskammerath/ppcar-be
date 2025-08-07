from pathlib import Path
from startup.shared.modules import import_modules_from

app_root = Path(__file__).parent

import_modules_from(package=app_root.name, module_name="models")
