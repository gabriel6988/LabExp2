import os
import requests
import subprocess
import csv

API_URL = "https://api.github.com/search/repositories?q=language:Java&sort=stars&order=desc&page={page}&per_page=100"

# Diretório para salvar os repositórios clonados
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.join(SCRIPT_DIR, "Cloned_Repositories")
os.makedirs(REPO_DIR, exist_ok=True)
clone_dir = 'Cloned_Repositories/'
ck_jar_path = "ck-0.7.1-SNAPSHOT-jar-with-dependencies.jar"

# Token do GitHub para autenticação para evitar limites de taxa
GITHUB_TOKEN = ''

# Função para obter os principais repositórios com autenticação
def get_top_repositories():
    repositories = []
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    
    for page in range(1, 11):  # Buscando os primeiros 1000 repositórios, 100 por página
        response = requests.get(API_URL.format(page=page), headers=headers)
        if response.status_code == 200:
            data = response.json()
            repositories.extend(data["items"])
        else:
            print(f"Falha ao buscar dados da página {page}")
    return repositories

# Função para clonar repositórios com profundidade 1 para reduzir dados buscados
def clone_repositories(repositories):
    failed_repos = []
    for repo in repositories:
        repo_name = repo["name"]
        clone_url = repo["clone_url"]
        repo_path = os.path.join(REPO_DIR, repo_name)

        if not os.path.exists(repo_path):
            print(f"Clonando {repo_name}...")
            try:
                subprocess.run(["git", "clone", "--depth", "1", clone_url, repo_path], check=True)
                print(f"Sucesso: {repo_name}")
            except subprocess.CalledProcessError:
                print(f"Falha ao clonar {repo_name}")
                failed_repos.append(repo)
        else:
            print(f"{repo_name} já existe")

    # Tentar novamente os que falharam
    if failed_repos:
        print(f"Tentando novamente {len(failed_repos)} repositórios...")
        clone_repositories(failed_repos)

def execute_ck_repositories(repositories):
    ck_executed = False
    for repo in repositories:
        if ck_executed == False:
            repo_name = repo["name"]
            repo_path = os.path.join(REPO_DIR, repo_name)

            if os.path.exists(repo_path):
                try:
                    result = subprocess.run(
                        ['java', '-jar', ck_jar_path, repo_path],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    
                    print("Saída do CK:")
                    print(result.stdout)
                    
                    ck_executed = True

                except subprocess.CalledProcessError as e:
                    print(f"Erro ao executar o CK: {e}")
                    print(f"Saída de erro: {e.stderr}")

def create_repositories_csv(repositories): 
    csv_file_path = "repositorios.csv"
    fieldnames = ["name", "stargazers_count", "forks_count", "clone_url"]

    with open(csv_file_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for repo in repositories:
            filtered_repo = {key: repo[key] for key in fieldnames if key in repo}
            writer.writerow(filtered_repo)
            
    print("Lista de repositórios criada: repositorios.csv")
                
                
# Função Main
def main():
    print("Buscando os 1000 principais repositórios Java...")
    repositories = get_top_repositories()
    create_repositories_csv(repositories)
    clone_repositories(repositories)
    execute_ck_repositories(repositories)

if __name__ == "__main__":
    main()
