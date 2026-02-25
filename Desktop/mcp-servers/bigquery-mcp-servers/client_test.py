import anyio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

TOKEN = "NDYzS8VqeS4LMYr4g_BEfWHwg_yKHfbiefHIGvGxqOo"

async def main():
    headers = {"Authorization": f"Bearer {TOKEN}"}

    async with sse_client("http://localhost:8080/sse", headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("TOOLS:", [t.name for t in tools.tools])

            res = await session.call_tool(
                "bigquery_select",
                {"sql": "SELECT 1 AS one", "max_rows": 10},
            )
            payload = getattr(res, "structuredContent", None) or getattr(res, "structured_content", None)
            print("RESULT:", payload)

            # optional: also print raw content blocks
            print("RAW CONTENT:", res.content)

anyio.run(main)