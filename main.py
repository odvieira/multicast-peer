import asyncio
import multiprocessing
from random import randint

from MulticastPeer import MulticastPeer

async def send_command(c:str, p:multiprocessing.Pipe) -> int:
	p.send(c)

	return 0

async def main():
    peer_pipe_rcv, peer_pipe_snd =  multiprocessing.Pipe(duplex=False) 

    peer = MulticastPeer(id=randint(0,100), pipe_end=peer_pipe_rcv)

    await asyncio.gather(
        peer.listen(),
        peer.active(),
				send_command('JOIN', peer_pipe_snd),
    )

if __name__ == '__main__':
    asyncio.run(main())

    