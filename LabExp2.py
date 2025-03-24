import os
import requests
import subprocess
import csv
import math

from datetime import datetime, date
from dateutil import relativedelta

API_URL = "https://api.github.com/search/repositories?q=language:Java&sort=stars&order=desc&page={page}&per_page=100"

# Diretório para salvar os repositórios clonados
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.join(SCRIPT_DIR, "Cloned_Repositories")
os.makedirs(REPO_DIR, exist_ok=True)
clone_dir = 'Cloned_Repositories/'
ck_jar_path = "ck-0.7.1-SNAPSHOT-jar-with-dependencies.jar"

# Token do GitHub para autenticação para evitar limites de taxa
GITHUB_TOKEN = ''
headers = {'Authorization': f'token {GITHUB_TOKEN}'}

# Função para obter os principais repositórios com autenticação
def get_top_repositories():
    repositories = []
    
    for page in range(1, 2):  # Buscando os primeiros 1000 repositórios, 100 por página
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
        
        if (check_repo_in_csv(repo["name"]) == False):
            owner = repo["owner"]["login"]
            rep_name = repo["name"]
            branch = repo["default_branch"]
            locNumber = countLinesInDirectory(rep_name)
            starsNumber =  repo["stargazers_count"]
            releasesNumber = getReleasesCount(owner, rep_name)
            maturity = getRepositoryOld(repo["created_at"])
        
        
            cbo_medio = ""
            mediana_cbo = ""
            desvio_padrao_cbo = ""
            dit_medio = ""
            mediana_dit = ""
            desvio_padrao_dit = ""
            lcom_medio = ""
            mediana_lcom = ""
            desvio_padrao_lcom = ""
            
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
                    
                    if (is_csv_empty('class.csv')):
                        ck_executed = False
                    else:
                        cbo_values = extract_from_csv('class.csv', 'cbo')
                        cbo_medio, mediana_cbo, desvio_padrao_cbo = getCboData(cbo_values)
                        
                        dit_values = extract_from_csv('class.csv', 'dit')
                        dit_medio, mediana_dit, desvio_padrao_dit = getDitData(dit_values)
                        
                        lcom_values = extract_from_csv('class.csv', 'lcom')
                        lcom_medio, mediana_lcom, desvio_padrao_lcom = getLcomData(lcom_values)
                        
                        repo_data = {
                            "name": repo_name,
                            "stargazers_count": starsNumber, 
                            "LOC": locNumber, 
                            "releases": releasesNumber,  
                            "maturity": maturity,  
                            "mediana_cbo": mediana_cbo,
                            "cbo_medio": cbo_medio,
                            "desvio_padrao_cbo": desvio_padrao_cbo,
                            "mediana_dit": mediana_dit,
                            "dit_medio": dit_medio,
                            "desvio_padrao_dit": desvio_padrao_dit,
                            "mediana_lcom": mediana_lcom,
                            "lcom_medio": lcom_medio,
                            "desvio_padrao_lcom": desvio_padrao_lcom
                        }
                        
                        write_to_csv(repo_data)
                    
                    print ("concluido")
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
                               
def main():
    print("Buscando os 1000 principais repositórios Java...")
    repositories = get_top_repositories()
    create_repositories_csv(repositories)
    clone_repositories(repositories)
    execute_ck_repositories(repositories)

def countLinesInDirectory(directory):
    
    total_lines = 0
    directoryOs = directory
    extensions = ['.java']
    
    for root, dirs, files in list(os.walk("Cloned_Repositories/" + directory)):
        for file in files:
            if extensions is None or os.path.splitext(file)[1] in extensions:
                file_path = os.path.join(root, file)
                total_lines += countLinesInFile(file_path)

    return total_lines

def countLinesInFile(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            return len(file.readlines())
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return 0

def getReleasesCount(owner, repo):
    releases_url = "https://api.github.com/repos/{owner}/{repo}/releases"
    page = 1
    releases_count = 0
    formatted_url = releases_url.format(owner=owner, repo=repo)
    
    while True:
        response = requests.get(f"{formatted_url}?page={page}&per_page=100", headers=headers)
        if (response.status_code == 200):
            releases = len(response.json())
            
            if not releases:
                break
            
            releases_count += releases
            page+=1
        else:
            print(response.status_code)
            break
            
    return releases_count

def getRepositoryOld(creationDate):
    start_date = datetime.strptime(creationDate, "%Y-%m-%dT%H:%M:%SZ")
    end_date = datetime.now()
    delta = relativedelta.relativedelta(end_date, start_date)
    return delta.years

def is_csv_empty(csv_path):
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return True

    with open(csv_path, mode='r', newline='') as csvfile:
        csvreader = csv.reader(csvfile)
        rows = list(csvreader)
        
        if len(rows) <= 1:
            return True
    return False

def extract_from_csv(class_csv_path, key):

    data_values = []

    try:
        with open(class_csv_path, mode='r', newline='') as csvfile:
            csvreader = csv.DictReader(csvfile)
            
            for row in csvreader:
                if key in row: 
                    data = row.get(key, '0')
                    
                    try:
                        data_values.append(int(data))
                    except ValueError:
                        continue
    except FileNotFoundError:
        print(f"File not found: {class_csv_path}")
    
    return data_values

def getMediumValue(values):
    sum = 0
    for value in values:
        sum += value
        
    return ("%.2f" % (sum/len(values)))

def getMedian(values):
    values.sort()

    n = len(values)

    if n % 2 != 0:
        return values[n // 2]
    else:
        middle1 = values[(n // 2) - 1]
        middle2 = values[n // 2]
        return (middle1 + middle2) / 2

def getStandardDeviation(values):
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(variance)

def getCboData(cbo_values):
    cbo_medio = getMediumValue(cbo_values)
    mediana_cbo = getMedian(cbo_values)
    desvio_padrao_cbo = getStandardDeviation(cbo_values)
    return {cbo_medio: cbo_medio, mediana_cbo: mediana_cbo, desvio_padrao_cbo: desvio_padrao_cbo}

def getDitData(dit_values):
    dit_medio = getMediumValue(dit_values)
    mediana_dit = getMedian(dit_values)
    desvio_padrao_dit = getStandardDeviation(dit_values)
    return {dit_medio: dit_medio, mediana_dit: mediana_dit, desvio_padrao_dit: desvio_padrao_dit}

def getLcomData(lcom_values):
    lcom_medio = getMediumValue(lcom_values)
    mediana_lcom = getMedian(lcom_values)
    desvio_padrao_lcom = getStandardDeviation(lcom_values)
    
    return lcom_medio, mediana_lcom, desvio_padrao_lcom

def write_to_csv(data):
    
    fieldnames = ["name", "stargazers_count", "LOC", "releases", "maturity", "mediana_cbo", "cbo_medio", 
                  "desvio_padrao_cbo", "mediana_dit", "dit_medio", "desvio_padrao_dit",
                  "mediana_lcom", "lcom_medio", "desvio_padrao_lcom"]
    
    file_exists = os.path.exists("resultados.csv")
    
    with open("resultados.csv", mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        writer.writerow(data)

import csv
import os

def check_repo_in_csv(repo_name):
    if not os.path.exists('resultados.csv'):
        return False  
    with open('resultados.csv', mode='r', newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        
        for row in reader:
            if len(row) > 0 and row[0] == repo_name:
                return True

    return False 

if __name__ == "__main__":
    main()
