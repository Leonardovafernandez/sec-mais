"""
Configuração de instalação do pacote SEC MAIS.

Permite instalar o projeto como um pacote Python
usando `pip install -e .` para desenvolvimento.
"""

from setuptools import find_packages, setup

setup(
    name="sec_mais",
    version="1.0.0",
    description="Plataforma de dados de políticas públicas educacionais - SEC-BA",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Secretaria de Educação do Estado da Bahia",
    python_requires=">=3.11",
    packages=find_packages(
        exclude=["tests*", "*.tests*", "dbt_sec_mais*", "airflow*"]
    ),
    install_requires=[
        "oracledb>=2.0.0",
        "psycopg2-binary>=2.9.9",
        "SQLAlchemy>=2.0.0",
        "pandas>=2.1.0",
        "pyarrow>=14.0.0",
        "python-dotenv>=1.0.0",
        "loguru>=0.7.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "spark": ["pyspark>=3.5.0"],
        "airflow": [
            "apache-airflow>=2.8.0",
            "apache-airflow-providers-oracle>=3.6.0",
        ],
        "dbt": [
            "dbt-core>=1.7.0",
            "dbt-duckdb>=1.7.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
        "all": [
            "pyspark>=3.5.0",
            "apache-airflow>=2.8.0",
            "dbt-core>=1.7.0",
            "dbt-duckdb>=1.7.0",
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    entry_points={
        "console_scripts": [
            "sec-mais-verificar=extracao.verificacao_conexao:executar_verificacao_completa",
        ],
    },
)
