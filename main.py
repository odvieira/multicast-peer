import asyncio
import multiprocessing
from random import randint
import tkinter
from tkinter import messagebox

from MulticastPeer import MulticastPeer

peer_pipe_rcv, peer_pipe_snd = multiprocessing.Pipe(duplex=False)


@asyncio.coroutine
def run_tk(root, interval=0.1):
    try:
        while True:
            root.update()
            yield from asyncio.sleep(interval)
    except tkinter.TclError as e:
        exit(0)
        # if "application has been destroyed" not in e.args[0]:
        # 	raise


def send_command_join() -> None:
    peer_pipe_snd.send('JOIN')


def send_command_request() -> None:
    peer_pipe_snd.send('RLOCK')


def send_command_exit() -> None:
    peer_pipe_snd.send('EXIT')

async def main():
    root_obj = tkinter.Tk()

    button_join = tkinter.Button(
        root_obj, text="Join", command=send_command_join)
    button_join.pack(side='top', expand=1)

    button_request = tkinter.Button(
        root_obj, text="Request", command=send_command_request)
    button_request.pack(side='top', expand=1)

    button_exit = tkinter.Button(
        root_obj, text="exit", command=send_command_exit)
    button_exit.pack(side='top', expand=1)

    peer = MulticastPeer(id=randint(0, 100), pipe_end=peer_pipe_rcv)

    await asyncio.gather(
        peer.listen(),
        peer.active(),
        run_tk(root_obj, 0.1)
    )

if __name__ == '__main__':
    asyncio.run(main())
