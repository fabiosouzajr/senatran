# Virtual Environment Information

This project uses a Python virtual environment located at:

**`.venv/`**

## Activation

### Linux/Mac:
```bash
source .venv/bin/activate
```

Or use the helper script:
```bash
source activate.sh
```

### Windows (PowerShell):
```powershell
.venv\Scripts\Activate.ps1
```

Or use the helper script:
```powershell
.\activate.ps1
```

## Deactivation

Simply run:
```bash
deactivate
```

## Verification

To verify the virtual environment is active, check:
```bash
which python  # Should point to .venv/bin/python
python --version
```

