import json
import os
import random
from datetime import datetime, timedelta
from github import Github, GithubException
from src.config import RAW_DATA_DIR, GITHUB_TOKEN, GITHUB_TOKENS, DEFAULT_REPO

class GitHubMiner:
    """Responsável por coletar dados do repositório GitHub e gerenciar o cache local."""

    def __init__(self, tokens=None, repo_name=DEFAULT_REPO):
        self.tokens = tokens or GITHUB_TOKENS
        self.repo_name = repo_name
        self.cache_file = RAW_DATA_DIR / f"{self.repo_name.replace('/', '_')}_data.json"
        
        self.clients = []
        if self.tokens:
            print(f"[INFO] Autenticado com {len(self.tokens)} token(s) do GitHub para rotação/divisão de carga.")
            for t in self.tokens:
                self.clients.append(Github(t))
        else:
            print("[WARN] Nenhum token do GitHub fornecido. Limites da API serão limitados (60 req/hora).")
            self.clients.append(Github())
            
        self.g = self.clients[0]

    def mine(self, limit=30, force_refresh=False):
        """
        Executa a mineração de dados utilizando múltiplos tokens se disponíveis.
        Divide o limite total de issues entre os tokens configurados.
        """
        if not force_refresh and self.cache_file.exists():
            print(f"[INFO] Carregando dados minerados do cache local: {self.cache_file.name}")
            return self.load_cache()

        limit_desc = f"{limit} itens" if limit > 0 else "sem limite (todos)"
        print(f"[INFO] Iniciando mineração ativa do repositório {self.repo_name} (Limite: {limit_desc})...")
        
        try:
            # Tenta checar o total de issues usando o primeiro cliente
            repo = self.g.get_repo(self.repo_name)
            issues_query = repo.get_issues(state="all")
            try:
                total_issues = issues_query.totalCount
                print(f"[INFO] Total de Issues/PRs no repositório: {total_issues}")
            except Exception:
                total_issues = 2000  # Fallback se não conseguir ler

            if limit > 0:
                total_to_process = min(limit, total_issues)
            else:
                total_to_process = total_issues

            issues_data = []
            prs_data = []
            
            # Dividir o total de itens igualmente entre os tokens disponíveis
            num_clients = len(self.clients)
            chunk_size = max(1, total_to_process // num_clients)
            
            print(f"[INFO] Dividindo carga de {total_to_process} itens entre {num_clients} tokens (~{chunk_size} itens por token)...")

            for c_idx, client in enumerate(self.clients):
                start_idx = c_idx * chunk_size
                # O último cliente pega até o final
                end_idx = total_to_process if c_idx == num_clients - 1 else (c_idx + 1) * chunk_size
                
                if start_idx >= total_to_process:
                    break

                print(f"\n[INFO] Token {c_idx+1}/{num_clients} iniciando mineração da fatia [{start_idx} a {end_idx}]...")

                try:
                    # Mostrar rate limit inicial deste token
                    try:
                        rl = client.get_rate_limit().core
                        print(f"  [STATUS] Token {c_idx+1} Rate Limit: {rl.remaining}/{rl.limit} (reseta em {rl.reset.astimezone()})")
                        if rl.remaining < 10:
                            print(f"  [WARN] Token {c_idx+1} possui poucas requisições restantes. Tentando prosseguir mesmo assim.")
                    except Exception:
                        pass

                    client_repo = client.get_repo(self.repo_name)
                    client_issues = client_repo.get_issues(state="all")[start_idx:end_idx]

                    for idx, issue in enumerate(client_issues):
                        global_idx = start_idx + idx + 1
                        print(f"  [{global_idx}/{total_to_process}] [Token {c_idx+1}] Processando #{issue.number}: {issue.title[:40]}...")

                        # Monitoramento periódico de rate limit do token atual a cada 50 itens
                        if (idx + 1) % 50 == 0:
                            try:
                                rl = client.get_rate_limit().core
                                print(f"    [STATUS Token {c_idx+1}] Rate Limit Restante: {rl.remaining}/{rl.limit}")
                                if rl.remaining < 10:
                                    print(f"    [WARN] Token {c_idx+1} esgotado! Salvando progresso e avançando para o próximo token...")
                                    break
                            except Exception:
                                pass

                        # Dados básicos do autor
                        author = issue.user.login if issue.user else "ghost"
                        author_avatar = issue.user.avatar_url if issue.user else ""
                        author_type = issue.user.type if issue.user else "User"

                        comments = []
                        # Coletando comentários da issue usando o cliente atual
                        try:
                            for comment in issue.get_comments():
                                c_author = comment.user.login if comment.user else "ghost"
                                comments.append({
                                    "author": c_author,
                                    "author_avatar": comment.user.avatar_url if comment.user else "",
                                    "author_type": comment.user.type if comment.user else "User",
                                    "created_at": comment.created_at.isoformat()
                                })
                        except Exception as ce:
                            print(f"    [WARN] Falha ao coletar comentários da issue #{issue.number}: {ce}")

                        is_pull_request = issue.pull_request is not None

                        item_data = {
                            "number": issue.number,
                            "title": issue.title,
                            "author": author,
                            "author_avatar": author_avatar,
                            "author_type": author_type,
                            "created_at": issue.created_at.isoformat(),
                            "comments": comments,
                            "is_pr": is_pull_request
                        }

                        if is_pull_request:
                            # Se for PR, coletamos revisões usando o cliente atual
                            try:
                                pr = client_repo.get_pull(issue.number)
                                reviews = []
                                for review in pr.get_reviews():
                                    r_author = review.user.login if review.user else "ghost"
                                    reviews.append({
                                        "author": r_author,
                                        "author_avatar": review.user.avatar_url if review.user else "",
                                        "author_type": review.user.type if review.user else "User",
                                        "state": review.state,
                                        "created_at": review.submitted_at.isoformat() if review.submitted_at else datetime.now().isoformat()
                                    })
                                item_data["reviews"] = reviews
                            except Exception as e:
                                item_data["reviews"] = []
                            prs_data.append(item_data)
                        else:
                            issues_data.append(item_data)

                except Exception as e:
                    print(f"[ERROR] Falha ao processar fatia com Token {c_idx+1}: {e}")
                    continue

            output_data = {
                "repository": self.repo_name,
                "mined_at": datetime.now().isoformat(),
                "issues": issues_data,
                "prs": prs_data
            }

            self.save_cache(output_data)
            print("\n[INFO] Mineração concluída com sucesso e dados armazenados em cache.")
            return output_data

        except GithubException as ge:
            print(f"[ERROR] Erro da API do GitHub: {ge}")
            if ge.status == 403:
                print("[ERROR] Limite de requisições excedido (Rate Limit) ou acesso não autorizado.")
            raise ge
        except Exception as e:
            print(f"[ERROR] Falha inesperada durante a mineração: {e}")
            raise e

    def save_cache(self, data):
        """Salva os dados coletados em formato JSON."""
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_cache(self):
        """Lê os dados do arquivo de cache."""
        with open(self.cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def generate_mock_data():
        """Gera dados realistas de contribuição do FastAPI para modo offline/simulado."""
        print("[INFO] Gerando dados sintéticos/mock realistas do repositório FastAPI...")
        
        # Principais contribuidores do FastAPI
        contributors = [
            {"username": "tiangolo", "avatar": "https://avatars.githubusercontent.com/u/13275653", "type": "User"},
            {"username": "dmontagu", "avatar": "https://avatars.githubusercontent.com/u/3511177", "type": "User"},
            {"username": "Kludex", "avatar": "https://avatars.githubusercontent.com/u/7362854", "type": "User"},
            {"username": "sobolevn", "avatar": "https://avatars.githubusercontent.com/u/4660274", "type": "User"},
            {"username": "samuelcolvin", "avatar": "https://avatars.githubusercontent.com/u/232162", "type": "User"},
            {"username": "tomchristie", "avatar": "https://avatars.githubusercontent.com/u/647385", "type": "User"},
            {"username": "euri10", "avatar": "https://avatars.githubusercontent.com/u/1271183", "type": "User"},
            {"username": "bueltge", "avatar": "https://avatars.githubusercontent.com/u/328220", "type": "User"},
            {"username": "dependabot", "avatar": "https://avatars.githubusercontent.com/u/49699333", "type": "Bot"},
            {"username": "matheus-soares", "avatar": "https://avatars.githubusercontent.com/u/123456", "type": "User"},
            {"username": "bernardo-cdm", "avatar": "https://avatars.githubusercontent.com/u/7891011", "type": "User"},
            {"username": "anonymous-coder", "avatar": "https://avatars.githubusercontent.com/u/000000", "type": "User"}
        ]
        
        issues = []
        prs = []
        base_date = datetime.now() - timedelta(days=90)
        
        # Gerar 40 itens simulados
        for i in range(1001, 1041):
            is_pr = random.choice([True, False])
            author = random.choice(contributors)
            
            # Não deixar dependabot criar issues, apenas PRs
            if not is_pr and author["username"] == "dependabot":
                author = random.choice([c for c in contributors if c["type"] == "User"])
                
            title = f"Fix bug in dependency injection" if is_pr else f"Error when parsing query parameters"
            if is_pr and author["username"] == "dependabot":
                title = "Bump pydantic from 2.5.2 to 2.6.0"
                
            created_at = base_date + timedelta(days=random.randint(1, 80), hours=random.randint(0, 23))
            
            # Gerar comentários de outros contribuidores
            comments = []
            num_comments = random.randint(0, 6)
            commenters = random.sample([c for c in contributors if c != author], min(num_comments, len(contributors)-1))
            
            for commenter in commenters:
                comments.append({
                    "author": commenter["username"],
                    "author_avatar": commenter["avatar"],
                    "author_type": commenter["type"],
                    "created_at": (created_at + timedelta(hours=random.randint(1, 48))).isoformat()
                })
                
            item_data = {
                "number": i,
                "title": f"{title} #{i}",
                "author": author["username"],
                "author_avatar": author["avatar"],
                "author_type": author["type"],
                "created_at": created_at.isoformat(),
                "comments": comments,
                "is_pr": is_pr
            }
            
            if is_pr:
                # Se for PR, gerar revisões
                reviews = []
                # dmontagu, Kludex e tiangolo costumam revisar muito
                reviewers = [c for c in contributors if c["username"] in ["tiangolo", "dmontagu", "Kludex"] and c != author]
                num_reviews = random.randint(0, len(reviewers))
                chosen_reviewers = random.sample(reviewers, num_reviews)
                
                for reviewer in chosen_reviewers:
                    reviews.append({
                        "author": reviewer["username"],
                        "author_avatar": reviewer["avatar"],
                        "author_type": reviewer["type"],
                        "state": random.choice(["APPROVED", "CHANGES_REQUESTED", "COMMENTED"]),
                        "created_at": (created_at + timedelta(hours=random.randint(2, 24))).isoformat()
                    })
                item_data["reviews"] = reviews
                prs.append(item_data)
            else:
                issues.append(item_data)
                
        return {
            "repository": DEFAULT_REPO,
            "mined_at": datetime.now().isoformat(),
            "issues": issues,
            "prs": prs,
            "is_mock": True
        }
