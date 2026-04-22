Write-Host "Creating virtual environment..."
python -m venv .venv

Write-Host "Activating virtual environment..."
.\.venv\Scripts\Activate.ps1

Write-Host "Installing project..."
pip install -U pip
pip install -e .

Write-Host "Checking FFmpeg..."
ffmpeg -version

Write-Host ""
Write-Host "Done. Example commands:"
Write-Host '  optimaster presets'
Write-Host '  optimaster analyze "C:\path\to\track.wav"'
Write-Host '  optimaster optimize "C:\path\to\track.wav" --output-dir ".\renders"'
