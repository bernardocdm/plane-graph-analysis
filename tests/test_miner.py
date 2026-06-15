"""
Testes unitários para o módulo de mineração (src/mining/miner.py).

Como a mineração real depende da API do GitHub (rede + autenticação), o
cliente `Github` é substituído por um mock (`unittest.mock.patch`) em todos
os testes abaixo. Isso permite validar a lógica de inicialização, rotação de
tokens, tratamento de rate limit/erros e a persistência de cache/checkpoint
sem depender de rede, credenciais ou do repositório real.
"""
import json
import time
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
from github import RateLimitExceededException
from src.mining.miner import GitHubMiner


def test_init_without_tokens(monkeypatch):
    """Sem tokens configurados, o miner deve operar em modo anônimo."""
    monkeypatch.setattr("src.mining.miner.GITHUB_TOKENS", [])

    with patch("src.mining.miner.Github") as MockGithub:
        miner = GitHubMiner(tokens=[], repo_name="org/repo")

        assert miner.tokens == [""]
        # Github() deve ter sido chamado sem argumentos (modo anônimo)
        MockGithub.assert_called_with()


def test_init_with_tokens():
    """Com tokens configurados, o cliente deve ser criado com o primeiro token."""
    with patch("src.mining.miner.Github") as MockGithub:
        miner = GitHubMiner(tokens=["t1", "t2"], repo_name="org/repo")

        assert miner.tokens == ["t1", "t2"]
        assert miner._token_index == 0
        MockGithub.assert_called_with("t1")


def test_rotate_token_cycles_between_multiple_tokens():
    """Com múltiplos tokens, _rotate_token deve avançar circularmente sem dormir."""
    with patch("src.mining.miner.Github"):
        miner = GitHubMiner(tokens=["t1", "t2"], repo_name="org/repo")
        assert miner._token_index == 0

        miner._rotate_token()
        assert miner._token_index == 1

        miner._rotate_token()
        assert miner._token_index == 0


def test_rotate_token_single_token_sleeps(monkeypatch):
    """Com 1 único token, _rotate_token deve aguardar (mockado) e manter o índice."""
    sleep_calls = []
    monkeypatch.setattr(time, "sleep", lambda s: sleep_calls.append(s))

    with patch("src.mining.miner.Github"):
        miner = GitHubMiner(tokens=["t1"], repo_name="org/repo")
        miner._rotate_token()

        assert miner._token_index == 0
        assert sleep_calls == [60]


def test_call_api_success_first_try():
    """_call_api deve retornar o resultado diretamente se fn() não levantar erro."""
    with patch("src.mining.miner.Github"):
        miner = GitHubMiner(tokens=["t1"], repo_name="org/repo")
        assert miner._call_api(lambda: 42) == 42


def test_call_api_retries_on_rate_limit(monkeypatch):
    """_call_api deve rotacionar o token e tentar novamente após rate limit."""
    monkeypatch.setattr(time, "sleep", lambda s: None)

    with patch("src.mining.miner.Github"):
        miner = GitHubMiner(tokens=["t1", "t2"], repo_name="org/repo")
        # Evita problemas de formatação de MagicMock no f-string de log
        miner.g.get_rate_limit.return_value.core.reset.strftime.return_value = "12:00:00"

        calls = {"n": 0}

        def flaky():
            calls["n"] += 1
            if calls["n"] == 1:
                raise RateLimitExceededException(403, {"message": "rate limit"}, {})
            return "ok"

        result = miner._call_api(flaky)

        assert result == "ok"
        assert calls["n"] == 2
        assert miner._token_index == 1


def test_call_api_raises_after_exhausting_all_tokens(monkeypatch):
    """_call_api deve levantar RuntimeError se todos os tokens estiverem com rate limit."""
    monkeypatch.setattr(time, "sleep", lambda s: None)

    with patch("src.mining.miner.Github"):
        miner = GitHubMiner(tokens=["t1", "t2"], repo_name="org/repo")
        miner.g.get_rate_limit.return_value.core.reset.strftime.return_value = "12:00:00"

        def always_fails():
            raise RateLimitExceededException(403, {"message": "rate limit"}, {})

        with pytest.raises(RuntimeError):
            miner._call_api(always_fails)

def test_save_and_load_cache(tmp_path, monkeypatch):
    """save_cache/load_cache devem persistir e recuperar os dados em JSON."""
    monkeypatch.setattr("src.mining.miner.RAW_DATA_DIR", tmp_path)

    with patch("src.mining.miner.Github"):
        miner = GitHubMiner(tokens=["t1"], repo_name="org/repo")

        data = {
            "repository": "org/repo",
            "issues": [{"number": 1, "author": "alice"}],
            "prs": []
        }
        miner.save_cache(data)
        assert miner.cache_file.exists()

        loaded = miner.load_cache()
        assert loaded == data


def test_save_checkpoint(tmp_path, monkeypatch):
    """_save_checkpoint deve gravar o progresso parcial com is_checkpoint=True."""
    monkeypatch.setattr("src.mining.miner.RAW_DATA_DIR", tmp_path)

    with patch("src.mining.miner.Github"):
        miner = GitHubMiner(tokens=["t1"], repo_name="org/repo")

        issues_data = [{"number": 1, "author": "alice"}]
        prs_data = []
        miner._save_checkpoint(issues_data, prs_data)

        assert miner.cache_file.exists()
        with open(miner.cache_file, "r", encoding="utf-8") as f:
            saved = json.load(f)

        assert saved["is_checkpoint"] is True
        assert saved["repository"] == "org/repo"
        assert saved["issues"] == issues_data
        assert saved["prs"] == prs_data

def test_mine_uses_existing_cache(tmp_path, monkeypatch):
    """mine() deve retornar os dados do cache sem chamar a API se o cache existir."""
    monkeypatch.setattr("src.mining.miner.RAW_DATA_DIR", tmp_path)

    with patch("src.mining.miner.Github"):
        miner = GitHubMiner(tokens=["t1"], repo_name="org/repo")

        cached_data = {
            "repository": "org/repo",
            "issues": [{"number": 1, "author": "alice"}],
            "prs": [],
            "is_checkpoint": False
        }
        miner.save_cache(cached_data)

        result = miner.mine(limit=10)

        assert result == cached_data
        # Como usou o cache, get_repo (e portanto a API) não deve ter sido chamado
        miner.g.get_repo.assert_not_called()


def test_mine_uses_checkpoint_cache(tmp_path, monkeypatch, capsys):
    """mine() deve identificar um cache parcial (checkpoint) e avisar o usuário."""
    monkeypatch.setattr("src.mining.miner.RAW_DATA_DIR", tmp_path)

    with patch("src.mining.miner.Github"):
        miner = GitHubMiner(tokens=["t1"], repo_name="org/repo")

        checkpoint_data = {
            "repository": "org/repo",
            "issues": [{"number": 1, "author": "alice"}],
            "prs": [],
            "is_checkpoint": True
        }
        miner.save_cache(checkpoint_data)

        result = miner.mine(limit=10)

        assert result == checkpoint_data
        captured = capsys.readouterr()
        assert "checkpoint parcial" in captured.out


def test_mine_with_no_cache_and_empty_repository(tmp_path, monkeypatch):
    """mine() sem cache deve consultar a API e salvar um resultado vazio
    quando o repositório não possui issues/PRs."""
    monkeypatch.setattr("src.mining.miner.RAW_DATA_DIR", tmp_path)

    with patch("src.mining.miner.Github"):
        miner = GitHubMiner(tokens=["t1"], repo_name="org/repo")

        # Configura o mock do rate limit para não quebrar os prints
        rate_limit_core = miner.g.get_rate_limit.return_value.core
        rate_limit_core.remaining = 5000
        rate_limit_core.limit = 5000
        rate_limit_core.reset.strftime.return_value = "12:00:00"

        # Configura o repositório/issues retornados pela API mockada
        issues_query = miner.g.get_repo.return_value.get_issues.return_value
        issues_query.totalCount = 0
        issues_query.__iter__.return_value = iter([])

        result = miner.mine(limit=10)

        assert result["repository"] == "org/repo"
        assert result["issues"] == []
        assert result["prs"] == []
        assert "mined_at" in result
        assert miner.cache_file.exists()


def test_mine_processes_single_issue_with_comment(tmp_path, monkeypatch):
    """mine() deve processar corretamente uma issue simples com um comentário,
    extraindo autor, comentários e marcando is_pr/closed_by corretamente."""
    monkeypatch.setattr("src.mining.miner.RAW_DATA_DIR", tmp_path)

    with patch("src.mining.miner.Github"):
        miner = GitHubMiner(tokens=["t1"], repo_name="org/repo")

        rate_limit_core = miner.g.get_rate_limit.return_value.core
        rate_limit_core.remaining = 5000
        rate_limit_core.limit = 5000
        rate_limit_core.reset.strftime.return_value = "12:00:00"

        # Usuário autor da issue
        fake_author = MagicMock()
        fake_author.login = "alice"
        fake_author.avatar_url = "http://avatar/alice"
        fake_author.type = "User"

        # Usuário que comentou
        fake_commenter = MagicMock()
        fake_commenter.login = "bob"
        fake_commenter.avatar_url = "http://avatar/bob"
        fake_commenter.type = "User"

        fake_comment = MagicMock()
        fake_comment.user = fake_commenter
        fake_comment.created_at = datetime(2024, 1, 1, 12, 0, 0)

        # Issue simulada (não é PR, está aberta)
        fake_issue = MagicMock()
        fake_issue.number = 1
        fake_issue.title = "Bug report"
        fake_issue.user = fake_author
        fake_issue.created_at = datetime(2024, 1, 1, 10, 0, 0)
        fake_issue.pull_request = None
        fake_issue.state = "open"
        fake_issue.get_comments.return_value = [fake_comment]

        issues_query = miner.g.get_repo.return_value.get_issues.return_value
        issues_query.totalCount = 1
        issues_query.__iter__.return_value = iter([fake_issue])

        result = miner.mine(limit=10)

        assert len(result["issues"]) == 1
        issue_data = result["issues"][0]
        assert issue_data["number"] == 1
        assert issue_data["title"] == "Bug report"
        assert issue_data["author"] == "alice"
        assert issue_data["is_pr"] is False
        assert issue_data["closed_by"] is None
        assert len(issue_data["comments"]) == 1
        assert issue_data["comments"][0]["author"] == "bob"
        assert result["prs"] == []