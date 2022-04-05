import asyncio
from MulticastPeer import MulticastPeer

async def main():
    for i in range(4):
        p = MulticastPeer(i)
        t = asyncio.create_task(p.join())
        await t
    

if __name__ == '__main__':
    asyncio.run(main())
