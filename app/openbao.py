import os

import httpx


class OpenBaoClient:
    def __init__(self):
        self.address = os.getenv(
            "OPENBAO_ADDRESS",
            "http://localhost:8200",
        ).rstrip("/")

        self.token = os.getenv("OPENBAO_TOKEN")

        if not self.token:
            raise RuntimeError("OPENBAO_TOKEN is not configured")

    def _headers(self):
        return {
            "X-Vault-Token": self.token,
        }

    async def request(self, method: str, path: str, **kwargs):
        url = f"{self.address}/v1/{path.lstrip('/')}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=self._headers(),
                **kwargs,
            )

        if response.is_error:
            raise RuntimeError(
                f"OpenBao returned HTTP {response.status_code}: "
                f"{response.text}"
            )

        if not response.text.strip():
            return {}

        return response.json()

    async def register_provider(
        self,
        name: str,
        client_id: str,
        client_secret: str,
    ):
        return await self.request(
            "PUT",
            f"oauth2/servers/{name}",
            json={
                "client_id": client_id,
                "client_secret": client_secret,
                "provider": name,
            },
        )

    async def create_auth_code_url(
        self,
        server: str,
        redirect_url: str,
        scopes: list[str],
        state: str,
    ):
        return await self.request(
            "POST",
            "oauth2/auth-code-url",
            json={
                "server": server,
                "redirect_url": redirect_url,
                "scopes": scopes,
                "state": state,
            },
        )

    async def exchange_code(
        self,
        name: str,
        server: str,
        code: str,
        redirect_url: str,
    ):
        return await self.request(
            "POST",
            f"oauth2/creds/{name}",
            json={
                "server": server,
                "code": code,
                "redirect_url": redirect_url,
            },
        )

    async def get_credential(
        self,
        name: str,
        server: str,
    ):
        return await self.request(
            "GET",
            f"oauth2/creds/{name}",
            json={
                "server": server,
            },
        )