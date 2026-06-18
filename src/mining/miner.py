import json
import time
from datetime import datetime
from github import Github, GithubException, RateLimitExceededException
from src.config import RAW_DATA_DIR, GITHUB_TOKENS, DEFAULT_REPO


# ==============================================================================
# Classe: GitHubMiner
# Descrição: Classe responsável pela mineração de dados de issues e PRs de um
#            repositório no GitHub. Implementa gerenciamento de múltiplos tokens
#            (rotação automática para evitar estouro de limites/rate limits) e
#            sistema de cache/checkpoints para evitar perdas de progresso.
# ==============================================================================
class GitHubMiner:
    """
    Responsável por coletar dados do repositório GitHub e gerenciar o cache local.
    Utiliza rotação automática de tokens: ao atingir rate limit em um token,
    troca para o próximo sem perder o item que estava sendo processado.
    Salva checkpoints a cada 100 itens para não perder progresso em caso de erro.
    """

    CHECKPOINT_INTERVAL = 100  # salvar cache a cada N itens processados

    def __init__(self, tokens=None, repo_name=DEFAULT_REPO):
        self.tokens = tokens or GITHUB_TOKENS
        self.repo_name = repo_name
        self.cache_file = RAW_DATA_DIR / f"{self.repo_name.replace('/', '_')}_data.json"
        self._token_index = 0

        if not self.tokens:
            print("[WARN] Nenhum token do GitHub fornecido. Rate limit: 60 req/hora (anônimo).")
            self.tokens = [""]

        self.g = self._make_client()
        valid = len([t for t in self.tokens if t])
        print(f"[INFO] {valid} token(s) configurado(s) para rotação automática.")

    # ── Gerenciamento de tokens ───────────────────────────────────────────────

    def _make_client(self):
        token = self.tokens[self._token_index]
        return Github(token) if token else Github()

    def _rotate_token(self):
        """Avança circularmente para o próximo token e recria o cliente."""
        previous = self._token_index
        self._token_index = (self._token_index + 1) % len(self.tokens)
        if self._token_index == previous:
            print("[WARN] Apenas 1 token configurado. Aguardando 60s para o rate limit resetar...")
            time.sleep(60)
        else:
            print(f"[INFO] Rotacionando: token #{previous + 1} → token #{self._token_index + 1}.")
        self.g = self._make_client()

    def _call_api(self, fn):
        """
        Executa fn() com retry automático ao detectar RateLimitExceeded ou 403.
        Tenta todos os tokens antes de desistir.
        Garante que NENHUM item é perdido por esgotamento de rate limit.
        """
        max_attempts = len(self.tokens) * 3
        attempts = 0
        while attempts < max_attempts:
            try:
                return fn()
            except RateLimitExceededException:
                try:
                    rl = self.g.get_rate_limit().core
                    print(f"[WARN] Rate limit no token #{self._token_index + 1} "
                          f"(reset em {rl.reset.strftime('%H:%M:%S')} UTC). Rotacionando...")
                except Exception:
                    print(f"[WARN] Rate limit no token #{self._token_index + 1}. Rotacionando...")
                self._rotate_token()
                attempts += 1
            except GithubException as ge:
                if ge.status == 403:
                    print(f"[WARN] 403 Forbidden no token #{self._token_index + 1}. Rotacionando...")
                    self._rotate_token()
                    attempts += 1
                else:
                    raise
        raise RuntimeError(
            f"[ERROR] Todos os {len(self.tokens)} token(s) esgotaram o rate limit. "
            "Aguarde o reset ou adicione tokens de outras contas GitHub."
        )

    def _check_rate_limit(self):
        """Exibe e retorna o número de requisições restantes no token ativo."""
        try:
            rl = self._call_api(lambda: self.g.get_rate_limit().core)
            print(f"  [RATE LIMIT] Token #{self._token_index + 1}: "
                  f"{rl.remaining}/{rl.limit} req restantes "
                  f"(reset {rl.reset.strftime('%H:%M:%S')} UTC)")
            return rl.remaining
        except Exception:
            return 9999

    # ── Checkpoint ────────────────────────────────────────────────────────────

    def _save_checkpoint(self, issues_data, prs_data):
        """
        Salva o progresso atual em disco.
        Chamado a cada CHECKPOINT_INTERVAL itens para garantir que o progresso
        não seja perdido em caso de rate limit total ou interrupção.
        """
        checkpoint = {
            "repository": self.repo_name,
            "mined_at": datetime.now().isoformat(),
            "issues": issues_data,
            "prs": prs_data,
            "is_checkpoint": True
        }
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, indent=2, ensure_ascii=False)
        print(f"  [CHECKPOINT] Progresso salvo: {len(issues_data)} issues, {len(prs_data)} PRs.")

    # ── Mineração principal ───────────────────────────────────────────────────

    def mine(self, limit=30, force_refresh=False):
        """
        Minera issues e PRs do repositório com rotação automática de tokens
        e salvamento progressivo de checkpoints.

        Coleta por item:
          - Issues: author, comments, closed_by
          - PRs:    author, comments, reviews, merged_by, merged

        Args:
            limit:         Número máximo de issues/PRs (0 = sem limite).
            force_refresh: Ignora cache existente e reinicia a mineração.
        """
        if not force_refresh and self.cache_file.exists():
            print(f"[INFO] Carregando dados do cache: {self.cache_file.name}")
            data = self.load_cache()
            is_checkpoint = data.get("is_checkpoint", False)
            if is_checkpoint:
                issues_count = len(data.get("issues", []))
                prs_count    = len(data.get("prs", []))
                print(f"[INFO] Cache é um checkpoint parcial: "
                      f"{issues_count} issues e {prs_count} PRs salvos até agora.")
                print("[INFO] Use --force-refresh para recomeçar do zero.")
            return data

        limit_desc = f"{limit} itens" if limit > 0 else "todos os itens (sem limite)"
        print(f"[INFO] Iniciando mineração de '{self.repo_name}' ({limit_desc})...")

        self._check_rate_limit()

        try:
            repo          = self._call_api(lambda: self.g.get_repo(self.repo_name))
            issues_query  = self._call_api(lambda: repo.get_issues(state="all"))

            try:
                total_issues = issues_query.totalCount
                print(f"[INFO] Total de itens no repositório: {total_issues}")
            except Exception:
                total_issues = None
                print("[INFO] Não foi possível obter o total. Prosseguindo sem contagem.")

            total_to_process = (
                min(limit, total_issues)
                if (limit > 0 and total_issues)
                else (total_issues or limit)
            )

            issues_data = []
            prs_data    = []
            processed   = 0

            for issue in issues_query:
                if limit > 0 and processed >= limit:
                    break

                processed += 1
                pct = f"{processed}/{total_to_process}" if total_to_process else str(processed)
                print(f"  [{pct}] Processando #{issue.number}: {issue.title[:55]}...")

                # Checkpoint periódico — salva progresso independente do que acontecer
                if processed % self.CHECKPOINT_INTERVAL == 0:
                    self._save_checkpoint(issues_data, prs_data)
                    remaining = self._check_rate_limit()
                    if remaining < 50:
                        print(f"  [WARN] Poucas requisições no token #{self._token_index + 1}. "
                              "Rotacionando preventivamente...")
                        self._rotate_token()
                        self._check_rate_limit()

                author        = issue.user.login       if issue.user else "ghost"
                author_avatar = issue.user.avatar_url  if issue.user else ""
                author_type   = issue.user.type        if issue.user else "User"

                # Comentários
                comments = []
                try:
                    for comment in self._call_api(lambda i=issue: i.get_comments()):
                        comments.append({
                            "author":       comment.user.login      if comment.user else "ghost",
                            "author_avatar": comment.user.avatar_url if comment.user else "",
                            "author_type":  comment.user.type       if comment.user else "User",
                            "created_at":   comment.created_at.isoformat()
                        })
                except Exception as ce:
                    print(f"    [WARN] Falha ao coletar comentários do item #{issue.number}: {ce}")

                is_pull_request = issue.pull_request is not None

                item_data = {
                    "number":       issue.number,
                    "title":        issue.title,
                    "author":       author,
                    "author_avatar": author_avatar,
                    "author_type":  author_type,
                    "created_at":   issue.created_at.isoformat(),
                    "comments":     comments,
                    "is_pr":        is_pull_request
                }

                if not is_pull_request:
                    # Coletar quem fechou a issue (necessário para o Grafo 2)
                    closed_by = None
                    try:
                        if issue.state == "closed":
                            events = self._call_api(lambda i=issue: list(i.get_events()))
                            for event in reversed(events):
                                if event.event == "closed" and event.actor:
                                    closed_by = event.actor.login
                                    break
                    except Exception:
                        pass
                    item_data["closed_by"] = closed_by
                    issues_data.append(item_data)

                else:
                    # Detalhes do PR: revisões e merged_by (necessários para o Grafo 3)
                    reviews   = []
                    merged    = False
                    merged_by = None
                    try:
                        pr = self._call_api(lambda i=issue: repo.get_pull(i.number))
                        try:
                            for review in self._call_api(lambda p=pr: p.get_reviews()):
                                reviews.append({
                                    "author":       review.user.login      if review.user else "ghost",
                                    "author_avatar": review.user.avatar_url if review.user else "",
                                    "author_type":  review.user.type       if review.user else "User",
                                    "state":        review.state,
                                    "created_at":   (review.submitted_at.isoformat()
                                                     if review.submitted_at
                                                     else datetime.now().isoformat())
                                })
                        except Exception as re_:
                            print(f"    [WARN] Falha ao coletar revisões do PR #{issue.number}: {re_}")

                        merged    = pr.merged
                        merged_by = pr.merged_by.login if pr.merged_by else None

                    except Exception as pe:
                        print(f"    [WARN] Falha ao coletar detalhes do PR #{issue.number}: {pe}")

                    item_data["reviews"]   = reviews
                    item_data["merged"]    = merged
                    item_data["merged_by"] = merged_by
                    prs_data.append(item_data)

            # Salvamento final (marca como completo, sem is_checkpoint)
            output_data = {
                "repository": self.repo_name,
                "mined_at":   datetime.now().isoformat(),
                "issues":     issues_data,
                "prs":        prs_data
            }
            self.save_cache(output_data)
            print(f"\n[INFO] Mineração concluída: {len(issues_data)} issues, {len(prs_data)} PRs.")
            return output_data

        except Exception as e:
            # Qualquer falha inesperada — salvar checkpoint antes de propagar
            if issues_data or prs_data:
                print(f"[ERROR] Erro durante a mineração: {e}")
                print(f"[INFO] Salvando checkpoint de emergência "
                      f"({len(issues_data)} issues, {len(prs_data)} PRs coletados até agora)...")
                self._save_checkpoint(issues_data, prs_data)
            raise

    # ── Cache ─────────────────────────────────────────────────────────────────

    def save_cache(self, data):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Cache salvo em: {self.cache_file.name}")

    def load_cache(self):
        with open(self.cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    # ── Mock ──────────────────────────────────────────────────────────────────

    @staticmethod
    def generate_mock_data():
        """
        Gera dados sintéticos realistas do makeplane/plane para modo offline.
        Inclui closed_by em issues e merged_by/merged em PRs,
        cobrindo todos os campos necessários para os 4 grafos.
        """
        import random
        from datetime import timedelta
        print("[INFO] Gerando dados mock do repositório makeplane/plane...")

        contributors = [
            {"username": "sriramveeraghanta", "avatar": "https://avatars.githubusercontent.com/u/9484953",  "type": "User"},
            {"username": "pablohashescobar",  "avatar": "https://avatars.githubusercontent.com/u/18600920", "type": "User"},
            {"username": "gurusainath",        "avatar": "https://avatars.githubusercontent.com/u/67518620", "type": "User"},
            {"username": "rahulramesha",       "avatar": "https://avatars.githubusercontent.com/u/71900764", "type": "User"},
            {"username": "nikhil-task",        "avatar": "https://avatars.githubusercontent.com/u/98703399", "type": "User"},
            {"username": "Prince-Shivaram",    "avatar": "https://avatars.githubusercontent.com/u/85993243", "type": "User"},
            {"username": "ChandanTeerth",      "avatar": "https://avatars.githubusercontent.com/u/68558541", "type": "User"},
            {"username": "KumarRoshan",        "avatar": "https://avatars.githubusercontent.com/u/14017",    "type": "User"},
            {"username": "BifrostTitan",       "avatar": "https://avatars.githubusercontent.com/u/23018",   "type": "User"},
            {"username": "plane-bot",          "avatar": "https://avatars.githubusercontent.com/u/49699333", "type": "Bot"},
            {"username": "dependabot",         "avatar": "https://avatars.githubusercontent.com/u/27347476", "type": "Bot"},
        ]

        human_contributors = [c for c in contributors if c["type"] == "User"]
        core_reviewers = [c for c in human_contributors
                          if c["username"] in ("sriramveeraghanta", "pablohashescobar", "gurusainath")]

        issues_data = []
        prs_data    = []
        base_date   = datetime.now() - timedelta(days=90)

        for i in range(1001, 1061):
            is_pr  = random.choice([True, False])
            author = random.choice(human_contributors)
            created_at = base_date + timedelta(days=random.randint(1, 85),
                                               hours=random.randint(0, 23))

            possible_commenters = [c for c in human_contributors if c != author]
            commenters = random.sample(possible_commenters,
                                       min(random.randint(0, 5), len(possible_commenters)))
            comments = [{
                "author":       c["username"],
                "author_avatar": c["avatar"],
                "author_type":  c["type"],
                "created_at":   (created_at + timedelta(hours=random.randint(1, 72))).isoformat()
            } for c in commenters]

            item_data = {
                "number":       i,
                "title":        (
                    f"Fix: {random.choice(['state management','drag-and-drop','API pagination','auth flow'])} #{i}"
                    if is_pr else
                    f"Bug: {random.choice(['workspace crash','issue not saving','filter broken','slow load'])} #{i}"
                ),
                "author":       author["username"],
                "author_avatar": author["avatar"],
                "author_type":  author["type"],
                "created_at":   created_at.isoformat(),
                "comments":     comments,
                "is_pr":        is_pr
            }

            if not is_pr:
                closer = None
                if random.random() > 0.3:
                    closer = random.choice([c for c in human_contributors if c != author])
                item_data["closed_by"] = closer["username"] if closer else None
                issues_data.append(item_data)
            else:
                possible_reviewers = [c for c in core_reviewers if c != author]
                chosen = random.sample(possible_reviewers,
                                       min(random.randint(0, len(possible_reviewers)),
                                           len(possible_reviewers)))
                reviews = [{
                    "author":       r["username"],
                    "author_avatar": r["avatar"],
                    "author_type":  r["type"],
                    "state":        random.choice(["APPROVED", "CHANGES_REQUESTED", "COMMENTED"]),
                    "created_at":   (created_at + timedelta(hours=random.randint(2, 48))).isoformat()
                } for r in chosen]

                merged = random.random() > 0.25
                merger = None
                if merged:
                    possible_mergers = [c for c in core_reviewers if c != author]
                    if possible_mergers:
                        merger = random.choice(possible_mergers)["username"]

                item_data["reviews"]   = reviews
                item_data["merged"]    = merged
                item_data["merged_by"] = merger
                prs_data.append(item_data)

        return {
            "repository": DEFAULT_REPO,
            "mined_at":   datetime.now().isoformat(),
            "issues":     issues_data,
            "prs":        prs_data,
            "is_mock":    True
        }