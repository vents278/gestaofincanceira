"""Optional end-to-end check: python tests/browser_smoke.py (system Chromium)."""

import os
import subprocess
import tempfile
import time
from datetime import date
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="finance-browser-") as tmp:
        env = {
            **os.environ,
            "DATABASE_URL": f"sqlite:///{tmp}/browser.db",
            "JWT_SECRET": "browser-test-only-secret-with-at-least-32-characters",
            "PORT": "8001",
        }
        subprocess.run(
            [str(ROOT / ".venv/bin/alembic"), "upgrade", "head"],
            cwd=ROOT,
            env=env,
            check=True,
        )
        with open(Path(tmp) / "server.log", "w") as log:
            server = subprocess.Popen(
                ["bash", "scripts/start.sh"], cwd=ROOT, env=env, stdout=log, stderr=log
            )
            try:
                for _ in range(80):
                    try:
                        urlopen("http://127.0.0.1:8001/health", timeout=1)
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Server not ready")
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        executable_path=os.getenv("CHROMIUM_PATH", "/usr/bin/chromium"),
                        headless=True,
                        args=["--no-sandbox"],
                    )
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto("http://127.0.0.1:8001")
                    page.get_by_role(
                        "button", name="Primeiro acesso? Criar meu grupo"
                    ).click()
                    page.get_by_label("Seu nome", exact=True).fill("Rita Teste")
                    page.get_by_label("Nome do grupo familiar").fill("Rita & Jean")
                    page.get_by_label("E-mail", exact=True).first.fill(
                        "rita@example.com"
                    )
                    page.get_by_label("Senha", exact=True).first.fill(
                        "browser-test-password"
                    )
                    page.get_by_role("button", name="Criar meu grupo →").click()
                    page.locator("#app").wait_for(state="visible")
                    page.get_by_role(
                        "button", name="Contas bancárias", exact=False
                    ).first.click()
                    page.get_by_role("button", name="+ Adicionar conta").click()
                    page.get_by_label("Nome da conta").fill("Conta conjunta")
                    page.get_by_label("Saldo inicial (R$)").fill("1000")
                    page.get_by_role("button", name="Criar conta", exact=True).click()
                    page.locator("#account-dialog").wait_for(state="hidden")
                    page.locator('nav [data-page="settings"]').click()
                    form = page.locator("#member-form")
                    form.locator('[name="name"]').fill("Jean Teste")
                    form.locator('[name="email"]').fill("jean@example.com")
                    form.locator('[name="password"]').fill("jean-test-password")
                    form.get_by_role(
                        "button", name="Adicionar integrante", exact=True
                    ).click()
                    form.wait_for(state="hidden")
                    page.locator('nav [data-page="expense"]').click()
                    page.get_by_role("button", name="+ Novo lançamento").click()
                    form = page.locator("#entry-form")
                    form.locator('[name="description"]').fill("Supermercado de teste")
                    form.locator('[name="amount"]').fill("100")
                    form.locator('[name="settled_date"]').fill(date.today().isoformat())
                    form.locator('[name="shared"]').check()
                    form.get_by_role("button", name="Salvar lançamento").click()
                    page.locator("#entry-dialog").wait_for(state="hidden")
                    page.get_by_role(
                        "button", name="Editar", exact=True
                    ).first.wait_for()
                    assert (
                        "Supermercado de teste"
                        in page.locator("#entry-table").inner_text()
                    )
                    page.get_by_role("button", name="Editar", exact=True).first.click()
                    form.locator('[name="amount"]').fill("120")
                    form.get_by_role("button", name="Salvar lançamento").click()
                    page.locator("#entry-dialog").wait_for(state="hidden")
                    page.wait_for_function(
                        "document.querySelector('#entry-table').textContent.includes('120,00')"
                    )
                    page.locator('nav [data-page="split"]').click()
                    assert "60,00" in page.locator("#settlement").inner_text()
                    page.locator('nav [data-page="dashboard"]').click()
                    page.wait_for_timeout(400)
                    assert page.locator("canvas").count() == 2
                    assert (
                        page.evaluate(
                            'Chart.getChart(document.querySelector("#flow-chart")).data.datasets[0].data[1]'
                        )
                        == 120
                    )
                    page.screenshot(path="/tmp/finance-desktop.png", full_page=True)
                    page.set_viewport_size({"width": 390, "height": 844})
                    page.wait_for_timeout(300)
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= innerWidth"
                    )
                    page.screenshot(path="/tmp/finance-mobile.png", full_page=True)
                    assert not errors, errors
                    browser.close()
                print(
                    "Browser smoke passed: register, account, member, shared expense, edit, split, charts, mobile layout; no JS errors."
                )
            finally:
                server.terminate()
                server.wait(timeout=10)


if __name__ == "__main__":
    main()
