import asyncio
from MulticastPeer import MulticastPeer
import sys

async def main():
    a, b = mp.Pipe()

    # peer = MulticastPeer(sys.argv[1])
    peer = MulticastPeer(1, pipe_end=a)
        
    asyncio.as_completed([
        peer.listen()
        peer.join()
    ])

    p.join(4)
    

if __name__ == '__main__':
    asyncio.run(main())
