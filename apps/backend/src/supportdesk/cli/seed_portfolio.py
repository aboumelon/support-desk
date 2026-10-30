"""Explicit production fixture templates; no reusable public staff credentials."""

import asyncio

from supportdesk.cli.seed_demo import seed as seed_workspaces
from supportdesk.cli.seed_knowledge import seed as seed_documents


async def main() -> None:
    await seed_workspaces(portfolio_template=True)
    await seed_documents(portfolio_template=True)


if __name__ == "__main__":
    asyncio.run(main())
