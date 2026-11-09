"""Ponto de entrada da simulação (FDD-0007, seção 3). Toda a lógica fica em autoseguro.interface.

Uso: uv run --env-file .env streamlit run ui-app/app.py
"""

from autoseguro.interface.layout import executar

executar()
