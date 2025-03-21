import os
import requests
import subprocess
import csv
import pandas as pd
from datetime import datetime
import glob

# URL da API do GitHub para pesquisar repositórios Java
API_URL = "https://api.github.com/search/repositories?q=language:Java&sort=stars&order=desc&page={page}&per_page=100"

# Diretório onde o script está localizado
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Diretório para armazenar repositórios clonados
REPO_DIR = os.path.join(SCRIPT_DIR, "Cloned_Repositories")

# Caminho completo para o arquivo CK JAR
ck_jar_path = os.path.join(SCRIPT_DIR, "ck-0.7.1-SNAPSHOT-jar-with-dependencies.jar")

# Token GitHub para autenticação
GITHUB_TOKEN = ''

# Função para buscar os principais repositórios Java do GitHub
def get_top_repositories():
    repositories = []
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    for page in range(1, 11):
        response = requests.get(API_URL.format(page=page), headers=headers)
        if response.status_code == 200:
            data = response.json()
            repositories.extend(data["items"])
        else:
            print(f"Failed to fetch data from page {page}")
    return repositories

# Função para clonar repositórios (ignorada se o diretório já existir)
def clone_repositories(repositories):
    failed_repos = []
    for repo in repositories:
        repo_name = repo["name"]
        clone_url = repo["clone_url"]
        repo_path = os.path.join(REPO_DIR, repo_name)

        if not os.path.exists(repo_path):
            print(f"Cloning {repo_name}...")
            try:
                # Cria o diretório pai se ele não existir
                os.makedirs(os.path.dirname(repo_path), exist_ok=True)
                subprocess.run(["git", "clone", clone_url, repo_path], check=True)
                print(f"Success: {repo_name}")
            except subprocess.CalledProcessError as e:
                print(f"Failed to clone {repo_name}: {e}")
                failed_repos.append(repo)
        else:
            print(f"{repo_name} already exists")

    if failed_repos:
        print(f"Retrying {len(failed_repos)} repositories...")
        clone_repositories(failed_repos)

# Função para obter o número de lançamentos de um repositório
def get_releases_count(repo_full_name):
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    url = f"https://api.github.com/repos/{repo_full_name}/releases"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return len(response.json())
        else:
            print(f"Error fetching releases for {repo_full_name}: {response.status_code}")
            return 0
    except requests.exceptions.RequestException as e:
        print(f"Connection error fetching releases for {repo_full_name}: {e}")
        return 0

# Função para calcular a idade de um repositório em anos
def calculate_age_years(created_at):
    created_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
    today = datetime.now()
    age = today - created_date
    return age.days // 365

# Função para executar a ferramenta CK em um repositório e extrair métricas
def execute_ck_repository(repo_path):
    try:
        print(f"Running CK on repository: {repo_path}")
        
        # Encontre todos os arquivos Java no repositório
        java_files = glob.glob(os.path.join(repo_path, "**", "*.java"), recursive=True)
        
        if not java_files:
            print(f"No Java files found in {repo_path}. Skipping analysis.")
            return None
        
        print(f"Java files found: {java_files}")
        
        # Execute a ferramenta CK para o repositório
        result = subprocess.run(
            ['java', '-jar', ck_jar_path, "."],
            check=True,
            capture_output=True,
            text=True,
            cwd=repo_path
        )
        
        # Imprima a saída e os erros da ferramenta CK
        print("CK output:")
        print(result.stdout)
        print("CK errors:")
        print(result.stderr)
        
        # Caminho para o arquivo de saída CK
        ck_output_file = os.path.join(repo_path, "class.csv")
        
        # Verifique se o arquivo de saída existe
        if not os.path.exists(ck_output_file):
            print(f"Error: CK output file not found at {ck_output_file}")
            return None
        
        # Leia o arquivo class.csv
        df_class = pd.read_csv(ck_output_file)
        
        # Calcular métricas necessárias
        metrics = {
            "loc": df_class['loc'].sum() if 'loc' in df_class.columns else 0,  # Total de linhas de código
            "cbo": df_class['cbo'].mean() if 'cbo' in df_class.columns else 0.0,  # CBO médio
            "dit": df_class['dit'].max() if 'dit' in df_class.columns else 0.0,  # DIT máximo
            "lcom": df_class['lcom'].mean() if 'lcom' in df_class.columns else 0.0,  # LCOM médio
        }
        
        return metrics
    except subprocess.CalledProcessError as e:
        print(f"Error running CK: {e}")
        print(f"Error output: {e.stderr}")
        return None
    except Exception as e:
        print(f"Error processing CK output file: {e}")
        return None

# Função para criar o arquivo CSV com dados do repositório
def create_repositories_csv(repositories):
    csv_file_path = "repositories.csv"
    fieldnames = [
        "name", "stargazers_count", "loc", "releases_count", "age_years", "cbo", "dit", "lcom"
    ]

    with open(csv_file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for repo in repositories:
            repo_name = repo["name"]
            repo_full_name = repo["full_name"]
            repo_path = os.path.join(REPO_DIR, repo_name)

            releases_count = get_releases_count(repo_full_name)
            age_years = calculate_age_years(repo["created_at"])
            ck_metrics = execute_ck_repository(repo_path) if os.path.exists(repo_path) else {}

            if ck_metrics is None:
                ck_metrics = {
                    "loc": 0,
                    "cbo": 0.0,
                    "dit": 0.0,
                    "lcom": 0.0,
                }
            else:
                ck_metrics.setdefault("loc", 0)
                ck_metrics.setdefault("cbo", 0.0)
                ck_metrics.setdefault("dit", 0.0)
                ck_metrics.setdefault("lcom", 0.0)

            row = {
                "name": repo_name,
                "stargazers_count": repo["stargazers_count"],
                "loc": ck_metrics["loc"],
                "releases_count": releases_count,
                "age_years": age_years,
                "cbo": ck_metrics["cbo"],
                "dit": ck_metrics["dit"],
                "lcom": ck_metrics["lcom"],
            }
            writer.writerow(row)
            
    print(f"CSV file created: {csv_file_path}")

# Main function
def main():
    print("Fetching top 100 Java repositories...")
    repositories = get_top_repositories()

    # Verifica se a pasta Cloned_Repositories já existe
    if os.path.exists(REPO_DIR) and os.path.isdir(REPO_DIR):
        print(f"Directory {REPO_DIR} already exists. Skipping cloning.")
    else:
        print(f"Directory {REPO_DIR} does not exist. Starting cloning process.")
        clone_repositories(repositories)

    create_repositories_csv(repositories)

if __name__ == "__main__":
    main()